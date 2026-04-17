from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import (
    AuditLogRecord,
    InviteRecord,
    OrganizationRecord,
    UserRecord,
    WorkspaceConfigRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
    async_session,
)
from app.models.schemas import AppConfig, OrganizationSummary, WorkspaceSummary
from app.services.pairs import get_available_pairs_catalog, select_default_enabled_pairs


logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class UserSession:
    user_id: str
    username: str
    role: str
    auth_mode: str
    token_version: int = 0


def _slugify_workspace(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"workspace-{secrets.token_hex(4)}"


def _slugify_organization(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"organization-{secrets.token_hex(4)}"


def _default_trial_ends_at() -> datetime:
    return utcnow() + timedelta(days=14)


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    if normalized.count("@") != 1:
        return None
    local_part, domain = normalized.split("@", 1)
    if not local_part or not domain or "." not in domain:
        return None
    return normalized


def _organization_to_summary(organization: OrganizationRecord | None) -> dict | None:
    if organization is None:
        return None
    return OrganizationSummary(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        plan=organization.plan,
        stripe_customer_id=organization.stripe_customer_id,
        subscription_status=organization.subscription_status,
        trial_ends_at=organization.trial_ends_at,
    ).model_dump()


async def _ensure_default_organization(session: AsyncSession) -> OrganizationRecord:
    organization = await session.scalar(select(OrganizationRecord).order_by(OrganizationRecord.created_at.asc()))
    if organization is not None:
        return organization

    organization = OrganizationRecord(
        name="Default Organization",
        slug="default-org",
        plan="trial",
        subscription_status="trialing",
        trial_ends_at=_default_trial_ends_at(),
    )
    session.add(organization)
    await session.flush()
    return organization


async def _get_organization_for_user_record(
    session: AsyncSession,
    user: UserRecord | None,
) -> OrganizationRecord | None:
    if user is None or not getattr(user, "organization_id", None):
        return None
    return await session.scalar(select(OrganizationRecord).where(OrganizationRecord.id == user.organization_id))


async def _ensure_user_organization(session: AsyncSession, user: UserRecord) -> OrganizationRecord:
    organization = await _get_organization_for_user_record(session, user)
    if organization is not None:
        return organization

    organization = await _ensure_default_organization(session)
    user.organization_id = organization.id
    user.updated_at = utcnow()
    await session.flush()
    return organization


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def hash_password(password: str, *, iterations: int = 390000) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=iterations,
        salt=_b64encode(salt),
        digest=_b64encode(derived),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, digest_b64 = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_str)
        salt = _b64decode(salt_b64)
        expected_digest = _b64decode(digest_b64)
    except Exception:
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)


def _sign_token_payload(payload: dict) -> str:
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(
        settings.effective_auth_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def _decode_token_payload(token: str) -> dict | None:
    if not token or "." not in token or not settings.effective_auth_secret:
        return None

    encoded_payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        settings.effective_auth_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except Exception:
        return None

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(time.time()):
        return None

    return payload


async def record_audit_event(
    action: str,
    *,
    actor_user_id: str | None = None,
    actor_username: str | None = None,
    workspace_id: str | None = None,
    status: str = "success",
    details: dict | None = None,
) -> None:
    async with async_session() as session:
        session.add(
            AuditLogRecord(
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                workspace_id=workspace_id,
                action=action,
                status=status,
                details=json.dumps(details or {}, ensure_ascii=True),
            )
        )
        await session.commit()


async def get_user_by_username(username: str) -> UserRecord | None:
    async with async_session() as session:
        return await session.scalar(select(UserRecord).where(UserRecord.username == username))


async def get_user_by_login(login: str) -> UserRecord | None:
    normalized_email = _normalize_email(login)
    async with async_session() as session:
        if normalized_email is None:
            return await session.scalar(select(UserRecord).where(UserRecord.username == login))
        return await session.scalar(
            select(UserRecord).where(
                or_(
                    UserRecord.username == login,
                    UserRecord.email == normalized_email,
                )
            )
        )


async def get_user_by_email(email: str) -> UserRecord | None:
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        return None
    async with async_session() as session:
        return await session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))


async def get_user_by_id(user_id: str) -> UserRecord | None:
    async with async_session() as session:
        return await session.scalar(select(UserRecord).where(UserRecord.id == user_id))


async def _list_workspace_rows_for_user(user_id: str) -> list[tuple[WorkspaceRecord, WorkspaceMembershipRecord]]:
    async with async_session() as session:
        result = await session.execute(
            select(WorkspaceRecord, WorkspaceMembershipRecord)
            .join(
                WorkspaceMembershipRecord,
                WorkspaceMembershipRecord.workspace_id == WorkspaceRecord.id,
            )
            .where(WorkspaceMembershipRecord.user_id == user_id)
            .order_by(WorkspaceRecord.created_at.asc())
        )
        return result.all()


async def list_user_workspaces(user_id: str) -> list[WorkspaceSummary]:
    rows = await _list_workspace_rows_for_user(user_id)
    return [
        WorkspaceSummary(
            id=workspace.id,
            slug=workspace.slug,
            name=workspace.name,
            role=membership.role,
            is_active=workspace.is_active,
        )
        for workspace, membership in rows
    ]


async def get_workspace_for_user(user_id: str, workspace_id: str) -> WorkspaceSummary | None:
    workspaces = await list_user_workspaces(user_id)
    for workspace in workspaces:
        if workspace.id == workspace_id:
            return workspace
    return None


async def _create_workspace_if_missing(
    *,
    owner_user: UserRecord,
    organization_id: str,
    name: str,
    slug: str,
    config: AppConfig,
) -> WorkspaceRecord:
    async with async_session() as session:
        workspace = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        if workspace is not None:
            return workspace

        workspace = WorkspaceRecord(
            organization_id=organization_id,
            slug=slug,
            name=name,
            owner_user_id=owner_user.id,
            is_active=True,
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMembershipRecord(
                workspace_id=workspace.id,
                user_id=owner_user.id,
                role="owner",
            )
        )
        session.add(
            WorkspaceConfigRecord(
                workspace_id=workspace.id,
                value=config.model_dump_json(),
            )
        )
        await session.commit()
        await session.refresh(workspace)
        return workspace


async def _default_workspace_config() -> AppConfig:
    enabled_pairs: list[str] = []
    try:
        pair_catalog = await get_available_pairs_catalog()
        enabled_pairs = select_default_enabled_pairs(pair_catalog)
    except Exception as exc:
        logger.warning("default_workspace_pair_catalog_unavailable error=%s", exc)

    return AppConfig(
        thresholds={
            "min_volatility_pct": settings.min_volatility_pct,
            "min_volume_brl": settings.min_volume_brl,
            "min_volume_brl_small": settings.min_volume_brl_small,
            "min_liquidity_units": settings.min_liquidity_units,
            "max_spread_pct": settings.max_spread_pct,
        },
        weights={
            "volatility": settings.weight_volatility,
            "volume": settings.weight_volume,
            "liquidity": settings.weight_liquidity,
            "spread": settings.weight_spread,
            "repetition": settings.weight_repetition,
        },
        enabled_pairs=enabled_pairs,
        scan_interval_seconds=settings.scan_interval_seconds,
        telegram_enabled=bool(settings.telegram_bot_token and settings.telegram_chat_id),
        telegram_bot_token=settings.telegram_bot_token,
        telegram_chat_id=settings.telegram_chat_id,
        novadax_api_key=settings.novadax_api_key,
        novadax_api_secret=settings.novadax_api_secret,
        mb_api_key=settings.mb_api_key,
        mb_api_secret=settings.mb_api_secret,
        binance_api_key=settings.binance_api_key,
        binance_api_secret=settings.binance_api_secret,
    )


async def ensure_admin_bootstrap() -> None:
    if not settings.admin_username or not settings.admin_password:
        return

    async with async_session() as session:
        default_organization = await _ensure_default_organization(session)
        existing = await session.scalar(select(UserRecord).where(UserRecord.username == settings.admin_username))
        if existing is None:
            existing = UserRecord(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                organization_id=default_organization.id,
                token_version=0,
                is_active=True,
                password_updated_at=utcnow(),
            )
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            created_user = True
        else:
            if not getattr(existing, "organization_id", None):
                existing.organization_id = default_organization.id
                existing.updated_at = utcnow()
                await session.commit()
            created_user = False

    workspace = await _create_workspace_if_missing(
        owner_user=existing,
        organization_id=existing.organization_id or default_organization.id,
        name="Default Workspace",
        slug="default",
        config=await _default_workspace_config(),
    )

    if created_user:
        await record_audit_event(
            "auth.bootstrap_user",
            actor_user_id=existing.id,
            actor_username=existing.username,
            workspace_id=workspace.id,
            details={"source": "environment"},
        )


async def authenticate_admin_credentials(username: str, password: str) -> UserSession | None:
    user = await get_user_by_login(username)
    if user is not None and user.is_active and verify_password(password, user.password_hash):
        return UserSession(
            user_id=user.id,
            username=user.username,
            role=user.role,
            auth_mode="database",
            token_version=int(user.token_version),
        )

    if settings.admin_username and settings.admin_password:
        valid_env_login = hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
            password,
            settings.admin_password,
        )
        if valid_env_login:
            bootstrap_user = await get_user_by_username(username)
            if bootstrap_user is not None:
                return UserSession(
                    user_id=bootstrap_user.id,
                    username=bootstrap_user.username,
                    role=bootstrap_user.role,
                    auth_mode="environment",
                    token_version=int(bootstrap_user.token_version),
                )

    return None


def issue_access_token(session: UserSession) -> str:
    now = int(time.time())
    expires_at = now + settings.access_token_ttl_minutes * 60
    payload = {
        "sub": session.user_id,
        "usr": session.username,
        "role": session.role,
        "ver": session.token_version,
        "mode": session.auth_mode,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "jti": secrets.token_hex(12),
    }
    return _sign_token_payload(payload)


def issue_refresh_token(session: UserSession) -> str:
    now = int(time.time())
    expires_at = now + settings.refresh_token_ttl_days * 24 * 3600
    payload = {
        "sub": session.user_id,
        "usr": session.username,
        "ver": session.token_version,
        "mode": session.auth_mode,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
        "jti": secrets.token_hex(16),
    }
    return _sign_token_payload(payload)


async def verify_refresh_token(token: str) -> UserSession | None:
    payload = _decode_token_payload(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    token_version = payload.get("ver", 0)
    auth_mode = payload.get("mode", "database")
    token_type = payload.get("type")

    if not isinstance(user_id, str) or not isinstance(token_version, int):
        return None
    if token_type != "refresh":
        return None

    user = await get_user_by_id(user_id)
    if user is None or not user.is_active or int(user.token_version) != token_version:
        return None

    return UserSession(
        user_id=user.id,
        username=user.username,
        role=user.role,
        auth_mode=auth_mode,
        token_version=int(user.token_version),
    )


async def verify_access_token(token: str) -> UserSession | None:
    payload = _decode_token_payload(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    username = payload.get("usr")
    role = payload.get("role", "member")
    token_version = payload.get("ver", 0)
    auth_mode = payload.get("mode", "database")
    token_type = payload.get("type")

    if not isinstance(user_id, str) or not isinstance(username, str) or not isinstance(token_version, int):
        return None
    if token_type != "access":
        return None

    user = await get_user_by_id(user_id)
    if user is None or not user.is_active or int(user.token_version) != token_version:
        return None

    return UserSession(
        user_id=user.id,
        username=user.username,
        role=user.role,
        auth_mode=auth_mode,
        token_version=int(user.token_version),
    )


def validate_legacy_admin_token(token: str | None) -> bool:
    return bool(token and settings.admin_token and hmac.compare_digest(token, settings.admin_token))


async def legacy_admin_session() -> UserSession | None:
    username = settings.admin_username or "legacy-admin"
    user = await get_user_by_username(username)
    if user is not None:
        return UserSession(
            user_id=user.id,
            username=user.username,
            role=user.role,
            auth_mode="legacy_token",
            token_version=int(user.token_version),
        )
    return UserSession(
        user_id="legacy-admin",
        username=username,
        role="admin",
        auth_mode="legacy_token",
        token_version=0,
    )


async def change_admin_password(
    *,
    actor: UserSession,
    current_password: str,
    new_password: str,
) -> UserSession:
    if len(new_password) < 12:
        raise ValueError("New password must be at least 12 characters long")

    async with async_session() as session:
        user = await session.scalar(select(UserRecord).where(UserRecord.id == actor.user_id))
        if user is None:
            raise ValueError("Authenticated user was not found")

        if not verify_password(current_password, user.password_hash):
            if not (settings.admin_username and settings.admin_password):
                raise ValueError("Current password is invalid")
            valid_env_login = hmac.compare_digest(user.username, settings.admin_username) and hmac.compare_digest(
                current_password,
                settings.admin_password,
            )
            if not valid_env_login:
                raise ValueError("Current password is invalid")

        user.password_hash = hash_password(new_password)
        user.token_version = int(user.token_version) + 1
        user.must_change_password = False
        user.password_updated_at = utcnow()
        user.updated_at = utcnow()
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "auth.password_changed",
        actor_user_id=user.id,
        actor_username=user.username,
        details={"token_version": int(user.token_version)},
    )
    return UserSession(
        user_id=user.id,
        username=user.username,
        role=user.role,
        auth_mode="database",
        token_version=int(user.token_version),
    )


async def create_workspace_for_user(actor: UserSession, name: str) -> WorkspaceSummary:
    if actor.role not in {"admin", "owner"}:
        raise ValueError("Only admins can create workspaces")

    slug = _slugify_workspace(name)

    async with async_session() as session:
        actor_user = await session.scalar(select(UserRecord).where(UserRecord.id == actor.user_id))
        if actor_user is None:
            raise ValueError("Authenticated user was not found")
        organization = await _ensure_user_organization(session, actor_user)

        existing = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        if existing is not None:
            raise ValueError("A workspace with this name already exists")

        workspace = WorkspaceRecord(
            organization_id=organization.id,
            name=name,
            slug=slug,
            owner_user_id=actor.user_id,
            is_active=True,
        )
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMembershipRecord(
                workspace_id=workspace.id,
                user_id=actor.user_id,
                role="owner",
            )
        )
        session.add(
            WorkspaceConfigRecord(
                workspace_id=workspace.id,
                value=(await _default_workspace_config()).model_dump_json(),
            )
        )
        await session.commit()
        await session.refresh(workspace)

    await record_audit_event(
        "workspace.created",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        workspace_id=workspace.id,
        details={"workspace_name": name, "workspace_slug": slug},
    )
    return WorkspaceSummary(id=workspace.id, slug=workspace.slug, name=workspace.name, role="owner", is_active=True)


async def get_user_session_metadata(session_info: UserSession) -> dict:
    user = await get_user_by_id(session_info.user_id)
    workspaces = await list_user_workspaces(session_info.user_id)

    organization = None
    if user is not None and getattr(user, "organization_id", None):
        async with async_session() as session:
            organization = await session.scalar(
                select(OrganizationRecord).where(OrganizationRecord.id == user.organization_id)
            )

    return {
        "user_id": session_info.user_id,
        "username": session_info.username,
        "email": getattr(user, "email", None),
        "role": session_info.role,
        "auth_mode": session_info.auth_mode,
        "token_version": session_info.token_version,
        "password_last_changed_at": user.password_updated_at.isoformat() if user and user.password_updated_at else None,
        "must_change_password": bool(getattr(user, "must_change_password", False)) if user else False,
        "onboarding_completed_at": (
            user.onboarding_completed_at.isoformat()
            if user and getattr(user, "onboarding_completed_at", None)
            else None
        ),
        "organization": _organization_to_summary(organization),
        "workspaces": [workspace.model_dump() for workspace in workspaces],
    }


_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,50}$")
_ALLOWED_ROLES = {"admin", "member"}
_WORKSPACE_ADMIN_ROLES = {"owner", "admin"}
_WORKSPACE_OWNER_ROLES = {"owner"}
_WORKSPACE_ROLE_PRIORITY = {
    "member": 1,
    "admin": 2,
    "owner": 3,
}


def _generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)


def _ensure_valid_email(email: str) -> str:
    normalized_email = _normalize_email(email)
    if normalized_email is None:
        raise ValueError("Invalid email address")
    return normalized_email


def _invite_status(invite: InviteRecord) -> str:
    if invite.used_at is not None:
        return "used"
    if invite.expires_at <= utcnow():
        return "expired"
    return "pending"


def _build_username_seed_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0].lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", local_part).strip("-._")
    if len(normalized) < 3:
        normalized = f"user-{normalized or secrets.token_hex(2)}"
    return normalized[:40]


async def _generate_unique_username(session: AsyncSession, email: str) -> str:
    base_username = _build_username_seed_from_email(email)
    candidate = base_username

    for _ in range(20):
        existing = await session.scalar(select(UserRecord).where(UserRecord.username == candidate))
        if existing is None:
            return candidate
        candidate = f"{base_username[:40]}-{secrets.token_hex(2)}"[:50]

    raise ValueError("Unable to generate a unique username for the invited user")


def _workspace_role_priority(role: str) -> int:
    return _WORKSPACE_ROLE_PRIORITY.get(role, 0)


async def _get_workspace_membership(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
) -> WorkspaceMembershipRecord | None:
    return await session.scalar(
        select(WorkspaceMembershipRecord).where(
            WorkspaceMembershipRecord.workspace_id == workspace_id,
            WorkspaceMembershipRecord.user_id == user_id,
        )
    )


async def _require_workspace_membership(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    allowed_roles: set[str] | None = None,
    missing_detail: str,
    forbidden_detail: str,
) -> WorkspaceMembershipRecord:
    membership = await _get_workspace_membership(session, workspace_id=workspace_id, user_id=user_id)
    if membership is None:
        raise PermissionError(missing_detail)
    if allowed_roles is not None and membership.role not in allowed_roles:
        raise PermissionError(forbidden_detail)
    return membership


def _ensure_assignable_workspace_role(*, actor_role: str, target_role: str) -> None:
    if target_role == "admin" and actor_role != "owner":
        raise PermissionError("Only workspace owners can assign admin role")


def _ensure_manageable_target_membership(*, actor_role: str, target_role: str) -> None:
    if _workspace_role_priority(actor_role) <= _workspace_role_priority(target_role):
        raise PermissionError("Workspace owners cannot manage other owners")


def _invite_to_dict(
    invite: InviteRecord,
    *,
    workspace: WorkspaceRecord,
    organization: OrganizationRecord,
) -> dict:
    return {
        "id": invite.id,
        "code": invite.code,
        "email": invite.email,
        "workspace_id": invite.workspace_id,
        "workspace_name": workspace.name,
        "organization_id": invite.organization_id,
        "organization_name": organization.name,
        "role": invite.role,
        "status": _invite_status(invite),
        "expires_at": invite.expires_at.isoformat(),
        "used_at": invite.used_at.isoformat() if invite.used_at else None,
        "created_at": invite.created_at.isoformat(),
    }


def _user_to_dict(user: UserRecord, *, workspace_role: str | None = None) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": getattr(user, "email", None),
        "role": workspace_role or user.role,
        "is_active": bool(user.is_active),
        "must_change_password": bool(getattr(user, "must_change_password", False)),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "password_last_changed_at": user.password_updated_at.isoformat() if user.password_updated_at else None,
        "created_by_user_id": getattr(user, "created_by_user_id", None),
        "token_version": int(user.token_version),
    }


async def list_users_for_workspace(workspace_id: str) -> list[dict]:
    async with async_session() as session:
        result = await session.execute(
            select(UserRecord, WorkspaceMembershipRecord)
            .join(WorkspaceMembershipRecord, WorkspaceMembershipRecord.user_id == UserRecord.id)
            .where(WorkspaceMembershipRecord.workspace_id == workspace_id)
            .order_by(UserRecord.created_at.asc(), UserRecord.username.asc())
        )
        rows = result.all()
    return [_user_to_dict(user, workspace_role=membership.role) for user, membership in rows]


async def list_invites_for_workspace(*, actor: UserSession, workspace_id: str) -> list[dict]:
    async with async_session() as session:
        await _require_workspace_membership(
            session,
            workspace_id=workspace_id,
            user_id=actor.user_id,
            allowed_roles=_WORKSPACE_OWNER_ROLES,
            missing_detail="Workspace access denied",
            forbidden_detail="Workspace owner role required",
        )

        workspace = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.id == workspace_id))
        if workspace is None:
            raise LookupError("Workspace not found")

        organization = await session.scalar(
            select(OrganizationRecord).where(OrganizationRecord.id == workspace.organization_id)
        )
        if organization is None:
            raise LookupError("Organization not found")

        result = await session.execute(
            select(InviteRecord)
            .where(InviteRecord.workspace_id == workspace_id)
            .order_by(InviteRecord.created_at.desc())
        )
        invites = result.scalars().all()
        return [
            _invite_to_dict(invite, workspace=workspace, organization=organization)
            for invite in invites
        ]


async def create_invite_for_workspace(
    *,
    actor: UserSession,
    workspace_id: str,
    email: str,
    role: str = "member",
    expires_in_days: int = 7,
) -> dict:
    if role not in _ALLOWED_ROLES:
        raise ValueError("Invalid role")
    if expires_in_days < 1 or expires_in_days > 30:
        raise ValueError("Invite expiry must be between 1 and 30 days")

    normalized_email = _ensure_valid_email(email)
    expires_at = utcnow() + timedelta(days=expires_in_days)

    async with async_session() as session:
        actor_membership = await _require_workspace_membership(
            session,
            workspace_id=workspace_id,
            user_id=actor.user_id,
            allowed_roles=_WORKSPACE_OWNER_ROLES,
            missing_detail="Workspace access denied",
            forbidden_detail="Workspace owner role required",
        )
        _ensure_assignable_workspace_role(actor_role=actor_membership.role, target_role=role)

        workspace = await session.scalar(
            select(WorkspaceRecord).where(WorkspaceRecord.id == workspace_id, WorkspaceRecord.is_active.is_(True))
        )
        if workspace is None:
            raise LookupError("Workspace not found")

        organization = await session.scalar(
            select(OrganizationRecord).where(OrganizationRecord.id == workspace.organization_id)
        )
        if organization is None:
            raise LookupError("Organization not found")

        existing_user = await session.scalar(
            select(UserRecord).where(UserRecord.email == normalized_email)
        )
        if existing_user is not None:
            raise ValueError("Email already belongs to an existing user")

        existing_invite = await session.scalar(
            select(InviteRecord).where(
                InviteRecord.workspace_id == workspace_id,
                InviteRecord.email == normalized_email,
                InviteRecord.used_at.is_(None),
                InviteRecord.expires_at > utcnow(),
            )
        )
        if existing_invite is not None:
            raise ValueError("An active invite already exists for this email in the workspace")

        invite = InviteRecord(
            code=secrets.token_urlsafe(24),
            email=normalized_email,
            organization_id=organization.id,
            workspace_id=workspace.id,
            role=role,
            created_by_user_id=actor.user_id,
            expires_at=expires_at,
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)

    await record_audit_event(
        "invite.created",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        workspace_id=workspace_id,
        details={
            "invite_id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "expires_at": invite.expires_at.isoformat(),
        },
    )
    return _invite_to_dict(invite, workspace=workspace, organization=organization)


async def get_invite_preview(code: str) -> dict:
    normalized_code = code.strip()
    if not normalized_code:
        raise LookupError("Invite not found")

    async with async_session() as session:
        invite = await session.scalar(select(InviteRecord).where(InviteRecord.code == normalized_code))
        if invite is None:
            raise LookupError("Invite not found")

        workspace = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.id == invite.workspace_id))
        organization = await session.scalar(
            select(OrganizationRecord).where(OrganizationRecord.id == invite.organization_id)
        )
        if workspace is None or organization is None:
            raise LookupError("Invite is no longer valid")

        return {
            "code": invite.code,
            "email": invite.email,
            "workspace_name": workspace.name,
            "organization_name": organization.name,
            "role": invite.role,
            "status": _invite_status(invite),
            "expires_at": invite.expires_at.isoformat(),
        }


async def accept_invite(*, code: str, email: str, password: str) -> UserSession:
    normalized_email = _ensure_valid_email(email)
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    async with async_session() as session:
        invite = await session.scalar(select(InviteRecord).where(InviteRecord.code == code.strip()))
        if invite is None:
            raise LookupError("Invite not found")
        if _invite_status(invite) != "pending":
            raise ValueError("Invite has expired or was already used")
        if invite.email != normalized_email:
            raise ValueError("Email does not match the invite")

        existing_user = await session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
        if existing_user is not None:
            raise ValueError("A user with this email already exists")

        workspace = await session.scalar(
            select(WorkspaceRecord).where(WorkspaceRecord.id == invite.workspace_id, WorkspaceRecord.is_active.is_(True))
        )
        if workspace is None:
            raise LookupError("Workspace not found")

        username = await _generate_unique_username(session, normalized_email)
        user = UserRecord(
            username=username,
            email=normalized_email,
            password_hash=hash_password(password),
            role=invite.role,
            organization_id=invite.organization_id,
            token_version=0,
            is_active=True,
            must_change_password=False,
            created_by_user_id=invite.created_by_user_id,
            password_updated_at=utcnow(),
            onboarding_completed_at=None,
        )
        session.add(user)
        await session.flush()
        session.add(
            WorkspaceMembershipRecord(
                workspace_id=workspace.id,
                user_id=user.id,
                role=invite.role,
            )
        )
        invite.used_at = utcnow()
        invite.updated_at = utcnow()
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "invite.accepted",
        actor_user_id=user.id,
        actor_username=user.username,
        workspace_id=workspace.id,
        details={
            "invite_code": code,
            "email": normalized_email,
            "organization_id": invite.organization_id,
        },
    )
    return UserSession(
        user_id=user.id,
        username=user.username,
        role=user.role,
        auth_mode="database",
        token_version=int(user.token_version),
    )


async def mark_onboarding_completed(*, actor: UserSession) -> dict:
    async with async_session() as session:
        user = await session.scalar(select(UserRecord).where(UserRecord.id == actor.user_id))
        if user is None:
            raise LookupError("Authenticated user was not found")
        user.onboarding_completed_at = utcnow()
        user.updated_at = utcnow()
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "user.onboarding_completed",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        details={"completed_at": user.onboarding_completed_at.isoformat()},
    )
    return {"completed": True, "completed_at": user.onboarding_completed_at.isoformat()}


async def create_user_by_admin(
    *,
    actor: UserSession,
    workspace_id: str,
    username: str,
    temporary_password: str | None = None,
    role: str = "member",
) -> tuple[dict, str]:
    normalized = username.strip()
    if not _USERNAME_PATTERN.match(normalized):
        raise ValueError("Invalid username (use 3-50 chars, letters/digits/._-)")

    if role not in _ALLOWED_ROLES:
        raise ValueError("Invalid role")

    effective_password = temporary_password or _generate_temporary_password()
    if len(effective_password) < 10:
        raise ValueError("Temporary password must be at least 10 characters long")

    async with async_session() as session:
        workspace = await session.scalar(
            select(WorkspaceRecord).where(WorkspaceRecord.id == workspace_id, WorkspaceRecord.is_active.is_(True))
        )
        if workspace is None:
            raise LookupError("Workspace not found")

        actor_membership = await _require_workspace_membership(
            session,
            workspace_id=workspace_id,
            user_id=actor.user_id,
            allowed_roles=_WORKSPACE_OWNER_ROLES,
            missing_detail="Workspace access denied",
            forbidden_detail="Workspace owner role required",
        )
        _ensure_assignable_workspace_role(actor_role=actor_membership.role, target_role=role)

        existing = await session.scalar(select(UserRecord).where(UserRecord.username == normalized))
        if existing is not None:
            raise ValueError("Username already in use")

        user = UserRecord(
            username=normalized,
            password_hash=hash_password(effective_password),
            role=role,
            organization_id=workspace.organization_id,
            token_version=0,
            is_active=True,
            must_change_password=True,
            created_by_user_id=actor.user_id,
            password_updated_at=utcnow(),
        )
        session.add(user)
        await session.flush()
        session.add(
            WorkspaceMembershipRecord(
                workspace_id=workspace_id,
                user_id=user.id,
                role=role,
            )
        )
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "user.created",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        workspace_id=workspace_id,
        details={"target_user_id": user.id, "target_username": user.username, "role": user.role},
    )
    return _user_to_dict(user, workspace_role=role), effective_password


async def set_user_active_state(*, actor: UserSession, workspace_id: str, user_id: str, is_active: bool) -> dict:
    if actor.user_id == user_id and not is_active:
        raise ValueError("Workspace owners cannot deactivate themselves")

    async with async_session() as session:
        actor_membership = await _require_workspace_membership(
            session,
            workspace_id=workspace_id,
            user_id=actor.user_id,
            allowed_roles=_WORKSPACE_OWNER_ROLES,
            missing_detail="Workspace access denied",
            forbidden_detail="Workspace owner role required",
        )

        target_membership = await _get_workspace_membership(session, workspace_id=workspace_id, user_id=user_id)
        if target_membership is None:
            raise LookupError("User not found in this workspace")
        _ensure_manageable_target_membership(
            actor_role=actor_membership.role,
            target_role=target_membership.role,
        )

        user = await session.scalar(select(UserRecord).where(UserRecord.id == user_id))
        if user is None:
            raise LookupError("User not found")

        user.is_active = is_active
        if not is_active:
            user.token_version = int(user.token_version) + 1
        user.updated_at = utcnow()
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "user.activated" if is_active else "user.deactivated",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        workspace_id=workspace_id,
        details={"target_user_id": user.id, "target_username": user.username},
    )
    return _user_to_dict(user, workspace_role=target_membership.role)


async def reset_user_password(*, actor: UserSession, workspace_id: str, user_id: str) -> tuple[dict, str]:
    temporary_password = _generate_temporary_password()

    async with async_session() as session:
        actor_membership = await _require_workspace_membership(
            session,
            workspace_id=workspace_id,
            user_id=actor.user_id,
            allowed_roles=_WORKSPACE_OWNER_ROLES,
            missing_detail="Workspace access denied",
            forbidden_detail="Workspace owner role required",
        )

        target_membership = await _get_workspace_membership(session, workspace_id=workspace_id, user_id=user_id)
        if target_membership is None:
            raise LookupError("User not found in this workspace")
        _ensure_manageable_target_membership(
            actor_role=actor_membership.role,
            target_role=target_membership.role,
        )

        user = await session.scalar(select(UserRecord).where(UserRecord.id == user_id))
        if user is None:
            raise LookupError("User not found")

        user.password_hash = hash_password(temporary_password)
        user.token_version = int(user.token_version) + 1
        user.must_change_password = True
        user.password_updated_at = utcnow()
        user.updated_at = utcnow()
        await session.commit()
        await session.refresh(user)

    await record_audit_event(
        "user.password_reset",
        actor_user_id=actor.user_id,
        actor_username=actor.username,
        workspace_id=workspace_id,
        details={"target_user_id": user.id, "target_username": user.username},
    )
    return _user_to_dict(user, workspace_role=target_membership.role), temporary_password


async def list_audit_logs(*, workspace_id: str | None = None, limit: int = 50) -> list[dict]:
    async with async_session() as session:
        query = select(AuditLogRecord)
        if workspace_id:
            query = query.where(AuditLogRecord.workspace_id == workspace_id)
        result = await session.execute(query.order_by(desc(AuditLogRecord.created_at)).limit(limit))
        rows = result.scalars().all()

    logs: list[dict] = []
    for row in rows:
        try:
            details = json.loads(row.details) if row.details else {}
        except json.JSONDecodeError:
            details = {"raw": row.details}

        logs.append(
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "actor_username": row.actor_username,
                "workspace_id": row.workspace_id,
                "action": row.action,
                "status": row.status,
                "details": details,
                "created_at": row.created_at.isoformat(),
            }
        )
    return logs
