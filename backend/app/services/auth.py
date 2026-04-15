from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.config import settings
from app.models.database import (
    AuditLogRecord,
    UserRecord,
    WorkspaceConfigRecord,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
    async_session,
)
from app.models.schemas import AppConfig, WorkspaceSummary


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    name: str,
    slug: str,
    config: AppConfig,
) -> WorkspaceRecord:
    async with async_session() as session:
        workspace = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        if workspace is not None:
            return workspace

        workspace = WorkspaceRecord(
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


def _default_workspace_config() -> AppConfig:
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
        existing = await session.scalar(select(UserRecord).where(UserRecord.username == settings.admin_username))
        if existing is None:
            existing = UserRecord(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                token_version=0,
                is_active=True,
                password_updated_at=utcnow(),
            )
            session.add(existing)
            await session.commit()
            await session.refresh(existing)
            created_user = True
        else:
            created_user = False

    workspace = await _create_workspace_if_missing(
        owner_user=existing,
        name="Default Workspace",
        slug="default",
        config=_default_workspace_config(),
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
    user = await get_user_by_username(username)
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
        existing = await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))
        if existing is not None:
            raise ValueError("A workspace with this name already exists")

        workspace = WorkspaceRecord(
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
                value=_default_workspace_config().model_dump_json(),
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
    return {
        "user_id": session_info.user_id,
        "username": session_info.username,
        "role": session_info.role,
        "auth_mode": session_info.auth_mode,
        "token_version": session_info.token_version,
        "password_last_changed_at": user.password_updated_at.isoformat() if user and user.password_updated_at else None,
        "workspaces": [workspace.model_dump() for workspace in workspaces],
    }


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
