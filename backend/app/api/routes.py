from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.api.websocket import manager
from app.config import settings
from app.models.schemas import (
    AvailablePairsResponse,
    AppConfig,
    ConfigResponse,
    DashboardResponse,
    DashboardSummaryResponse,
    DashboardStats,
    ExchangeCredentialValidationResponse,
    Exchange,
    FilterThresholds,
    HistorySummaryRecord,
    InvitePreviewResponse,
    InviteRecordResponse,
    Opportunity,
    OpportunitySummary,
    PairExchangeDiagnosticResponse,
    ScoreWeights,
    SignalFeedbackCreate,
    SignalFeedbackResponse,
    UserCreateResponse,
    UserRecordResponse,
    UserSessionResponse,
    WorkspaceStatusResponse,
    WorkspaceSummary,
)
from app.filters.executability import classify_opportunity_type
from app.services.auth import (
    UserSession,
    accept_invite,
    authenticate_admin_credentials,
    change_admin_password,
    create_invite_for_workspace,
    create_user_by_admin,
    create_workspace_for_user,
    ensure_admin_bootstrap,
    get_invite_preview,
    get_user_session_metadata,
    get_workspace_for_user,
    issue_access_token,
    issue_refresh_token,
    legacy_admin_session,
    list_audit_logs,
    list_invites_for_workspace,
    list_users_for_workspace,
    mark_onboarding_completed,
    list_user_workspaces,
    record_audit_event,
    reset_user_password,
    set_user_active_state,
    validate_legacy_admin_token,
    verify_access_token,
    verify_refresh_token,
)
from app.services.monitoring import scan_monitor
from app.services.operational_visibility import (
    enrich_alert_worthiness,
    enrich_operational_visibility,
    is_operationally_visible,
)
from app.services.pairs import get_available_pairs_catalog, get_pair_exchange_diagnostic
from app.services.exchange_credentials import validate_exchange_credentials
from app.services.shared_state import (
    create_signal_feedback,
    get_missed_signal_diagnostic,
    get_near_misses,
    get_scanner_runtime_state,
    read_opportunity_snapshots,
)
from app.services.persistence import (
    DEFAULT_WORKSPACE_ID,
    get_filtered_analytics,
    get_workspace_operability_fields,
    get_history,
    get_history_summary,
    get_workspace_score,
    load_config,
    load_workspace_config,
    opportunity_matches_config,
    save_workspace_config,
)
from app.services.scan_runtime import request_scan_refresh
from app.services.telegram import send_telegram_test_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_SENSITIVE_CONFIG_FIELDS = {
    "telegram_bot_token",
    "telegram_chat_id",
    "novadax_api_key",
    "novadax_api_secret",
    "mb_api_key",
    "mb_api_secret",
    "binance_api_key",
    "binance_api_secret",
}

_current_opportunities: list[Opportunity] = []
_last_scan: datetime | None = None
_scan_config: AppConfig = AppConfig()


def update_state(opportunities: list[Opportunity], scan_time: datetime) -> None:
    global _current_opportunities, _last_scan
    _current_opportunities = opportunities
    _last_scan = scan_time


def get_scan_config() -> AppConfig:
    return _scan_config


def set_scan_config(config: AppConfig) -> None:
    global _scan_config
    _scan_config = config


def sanitize_config(config: AppConfig) -> AppConfig:
    data = config.model_dump()
    for field in _SENSITIVE_CONFIG_FIELDS:
        data[field] = ""
    return AppConfig(**data)


def build_config_response(config: AppConfig) -> ConfigResponse:
    return ConfigResponse(
        config=sanitize_config(config),
        configured_secrets={
            field: bool(getattr(config, field, ""))
            for field in sorted(_SENSITIVE_CONFIG_FIELDS)
        },
    )


async def get_optional_user_session(
    x_admin_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> UserSession | None:
    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization[7:].strip()

    if bearer_token:
        session_info = await verify_access_token(bearer_token)
        if session_info is not None:
            return session_info

    if x_admin_token:
        session_info = await verify_access_token(x_admin_token)
        if session_info is not None:
            return session_info
        if validate_legacy_admin_token(x_admin_token):
            return await legacy_admin_session()

    return None


async def require_user_session(
    session_info: UserSession | None = Depends(get_optional_user_session),
) -> UserSession:
    if session_info is not None:
        return session_info

    if not settings.admin_token and not settings.effective_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on the server",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )


async def resolve_workspace_context(
    session_info: UserSession | None,
    workspace_id: str | None,
) -> tuple[WorkspaceSummary, AppConfig]:
    if session_info is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    workspaces = await list_user_workspaces(session_info.user_id)
    if not workspaces:
        if session_info.auth_mode == "legacy_token":
            if workspace_id and workspace_id != DEFAULT_WORKSPACE_ID:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")

            config = await load_workspace_config(DEFAULT_WORKSPACE_ID) or await load_config() or AppConfig()
            return (
                WorkspaceSummary(
                    id=DEFAULT_WORKSPACE_ID,
                    slug="default",
                    name="Default Workspace",
                    role="owner",
                    is_active=True,
                ),
                config,
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace access")

    if workspace_id:
        workspace = await get_workspace_for_user(session_info.user_id, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    else:
        workspace = workspaces[0]

    config = await load_workspace_config(workspace.id)
    if config is None:
        config = await load_config() if workspace.id == DEFAULT_WORKSPACE_ID else AppConfig()
    return workspace, config


def project_workspace_opportunity(opportunity: Opportunity, config: AppConfig) -> Opportunity | None:
    if not opportunity_matches_config(opportunity, config):
        return None

    data = opportunity.model_dump()
    data["score"] = get_workspace_score(
        volatility_score=opportunity.volatility_score,
        volume_score=opportunity.volume_score,
        liquidity_score=opportunity.liquidity_score,
        spread_score=opportunity.spread_score,
        repetition_score=opportunity.repetition_score,
        movement_type=opportunity.movement_type.value,
        historical_confidence=opportunity.historical_confidence,
        weights=config.weights,
    )
    if opportunity.is_late_entry_risk:
        data["score"] = min(max(round(data["score"] * 0.9, 1), 0), 100)
    operability = get_workspace_operability_fields(
        bid_notional_top_n=opportunity.bid_notional_top_n,
        ask_notional_top_n=opportunity.ask_notional_top_n,
        spread_pct=opportunity.spread_pct,
        quote_volume_24h=opportunity.quote_volume_24h,
        fillable_notional_within_slippage_cap=opportunity.fillable_notional_within_slippage_cap,
        baseline_order_notional_brl=opportunity.baseline_order_notional_brl,
        estimated_buy_slippage_bps=opportunity.estimated_buy_slippage_bps,
        estimated_sell_slippage_bps=opportunity.estimated_sell_slippage_bps,
        movement_persistence_score=opportunity.movement_persistence_score,
        config=config,
    )
    data.update(operability)
    if (
        data.get("opportunity_type") != "avoid"
        and data.get("executability_score") is not None
        and data.get("trade_margin_score") is not None
        and data.get("estimated_net_trade_edge_pct") is not None
    ):
        data["opportunity_type"] = classify_opportunity_type(
            operable_signal=data.get("operable_signal"),
            interesting_signal=data.get("interesting_signal"),
            executability_score=data.get("executability_score"),
            trade_margin_score=data.get("trade_margin_score"),
            estimated_net_trade_edge_pct=data.get("estimated_net_trade_edge_pct"),
            movement_regime=(
                data.get("movement_regime").value
                if hasattr(data.get("movement_regime"), "value")
                else data.get("movement_regime")
            ),
        )
    return enrich_alert_worthiness(enrich_operational_visibility(Opportunity(**data)))


def build_dashboard_stats(
    *,
    opportunities: list[Opportunity],
    monitored_pairs: int,
    last_scan: datetime | None,
) -> DashboardStats:
    exchanges_online = len({opportunity.exchange for opportunity in opportunities})
    return DashboardStats(
        total_opportunities=len(opportunities),
        active_opportunities=len([opportunity for opportunity in opportunities if opportunity.score >= 40]),
        monitored_pairs=monitored_pairs,
        total_volume_24h=sum(opportunity.quote_volume_24h for opportunity in opportunities),
        best_score=max((opportunity.score for opportunity in opportunities), default=0),
        exchanges_online=exchanges_online,
        arbitrage_opportunities=len([opportunity for opportunity in opportunities if opportunity.arbitrage_available]),
        operable_opportunities=len([opportunity for opportunity in opportunities if opportunity.operable_signal]),
        trade_opportunities=len([opportunity for opportunity in opportunities if opportunity.opportunity_type == "trade"]),
        hold_opportunities=len([opportunity for opportunity in opportunities if opportunity.opportunity_type == "hold"]),
        observe_opportunities=len([opportunity for opportunity in opportunities if opportunity.opportunity_type == "observe"]),
        avoid_opportunities=len([opportunity for opportunity in opportunities if opportunity.opportunity_type == "avoid"]),
        last_scan=last_scan,
    )


async def get_monitored_pair_count(config: AppConfig) -> int:
    if config.pair_universe_mode == "watchlist_only":
        return len(config.enabled_pairs)

    try:
        scanner_state = await get_scanner_runtime_state()
    except Exception as exc:
        logger.debug("monitored_pair_count_state_unavailable error=%s", exc)
        scanner_state = None
    diagnostics = (scanner_state or {}).get("last_scan_diagnostics") or {}
    try:
        total_pairs = int(diagnostics.get("total_pairs") or 0)
    except (TypeError, ValueError):
        total_pairs = 0
    return total_pairs or len(config.enabled_pairs)


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class WorkspaceCreateRequest(BaseModel):
    name: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreateRequest(BaseModel):
    username: str
    temporary_password: str | None = None
    role: str = "member"


class UserUpdateRequest(BaseModel):
    is_active: bool


class TelegramTestRequest(BaseModel):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


class InviteCreateRequest(BaseModel):
    email: str
    role: str = "member"
    expires_in_days: int = 7


class InviteAcceptRequest(BaseModel):
    code: str
    email: str
    password: str


class ExchangeCredentialValidationRequest(BaseModel):
    novadax_api_key: str | None = None
    novadax_api_secret: str | None = None
    mb_api_key: str | None = None
    mb_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None


def require_workspace_admin_role(workspace: WorkspaceSummary) -> None:
    if workspace.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace admin role required")


def require_workspace_owner_role(workspace: WorkspaceSummary) -> None:
    if workspace.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace owner role required")


class ConfigUpdate(BaseModel):
    thresholds: FilterThresholds | None = None
    weights: ScoreWeights | None = None
    pair_universe_mode: Literal["all_brl", "watchlist_only"] | None = None
    enabled_exchanges: list[Exchange] | None = None
    enabled_pairs: list[str] | None = None
    scan_interval_seconds: int | None = None
    trading_profile: str | None = None
    order_notional_brl: float | None = None
    max_entry_slippage_bps: float | None = None
    max_exit_slippage_bps: float | None = None
    min_quote_volume_brl: float | None = None
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_alert_threshold: float | None = None
    telegram_alert_cooldown_seconds: int | None = None
    telegram_daily_alert_limit: int | None = None
    telegram_alert_types: list[str] | None = None
    telegram_operable_only: bool | None = None
    telegram_min_executability_score: float | None = None
    telegram_alert_exchanges: list[Exchange] | None = None
    telegram_alert_pairs: list[str] | None = None
    novadax_api_key: str | None = None
    novadax_api_secret: str | None = None
    mb_api_key: str | None = None
    mb_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None


def merge_config_with_sensitive_overrides(
    current_config: AppConfig,
    update_data: dict[str, object],
) -> AppConfig:
    data = current_config.model_dump()
    sanitized_update = dict(update_data)
    for field in _SENSITIVE_CONFIG_FIELDS:
        if sanitized_update.get(field, None) == "":
            sanitized_update.pop(field)
    data.update(sanitized_update)
    return AppConfig(**data)


async def build_workspace_status_response(
    *,
    session_info: UserSession,
    workspace: WorkspaceSummary,
    config: AppConfig,
) -> dict:
    session_metadata = await get_user_session_metadata(session_info)
    return {
        "workspace": workspace.model_dump(),
        "organization": session_metadata.get("organization"),
        "configured_pairs_count": len(config.enabled_pairs),
        "enabled_exchange_count": len(config.enabled_exchanges),
        "telegram_configured": bool(config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id),
        "exchange_credentials_configured": {
            "novadax": bool(config.novadax_api_key and config.novadax_api_secret),
            "mercado_bitcoin": bool(config.mb_api_key and config.mb_api_secret),
            "binance": bool(config.binance_api_key and config.binance_api_secret),
        },
        "onboarding_completed_at": session_metadata.get("onboarding_completed_at"),
    }


@router.post("/auth/login")
@router.post("/admin/login")
async def auth_login(payload: AuthLoginRequest):
    await ensure_admin_bootstrap()

    if not settings.effective_auth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session login is not configured on the server",
        )

    session_info = await authenticate_admin_credentials(payload.username, payload.password)
    if session_info is None:
        await record_audit_event(
            "auth.login",
            actor_username=payload.username,
            status="denied",
            details={"reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = issue_access_token(session_info)
    refresh_token = issue_refresh_token(session_info)
    await record_audit_event(
        "auth.login",
        actor_user_id=session_info.user_id,
        actor_username=session_info.username,
        details={"auth_mode": session_info.auth_mode},
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
        "refresh_expires_in_seconds": settings.refresh_token_ttl_days * 24 * 3600,
        "session": await get_user_session_metadata(session_info),
    }


@router.post("/auth/refresh")
async def auth_refresh(payload: RefreshTokenRequest):
    session_info = await verify_refresh_token(payload.refresh_token)
    if session_info is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = issue_access_token(session_info)
    refresh_token = issue_refresh_token(session_info)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
        "refresh_expires_in_seconds": settings.refresh_token_ttl_days * 24 * 3600,
        "session": await get_user_session_metadata(session_info),
    }


@router.get("/invites/{code}", response_model=InvitePreviewResponse)
async def invite_preview(code: str):
    try:
        return await get_invite_preview(code)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/invites/accept")
async def invite_accept(payload: InviteAcceptRequest):
    try:
        session_info = await accept_invite(code=payload.code, email=payload.email, password=payload.password)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_token = issue_access_token(session_info)
    refresh_token = issue_refresh_token(session_info)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
        "refresh_expires_in_seconds": settings.refresh_token_ttl_days * 24 * 3600,
        "session": await get_user_session_metadata(session_info),
    }


@router.get("/auth/session", response_model=UserSessionResponse)
@router.get("/admin/session", response_model=UserSessionResponse)
async def auth_session(session_info: UserSession = Depends(require_user_session)):
    return await get_user_session_metadata(session_info)


@router.post("/auth/change-password")
@router.post("/admin/change-password")
async def auth_change_password(
    payload: PasswordChangeRequest,
    session_info: UserSession = Depends(require_user_session),
):
    try:
        updated_session = await change_admin_password(
            actor=session_info,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_token = issue_access_token(updated_session)
    refresh_token = issue_refresh_token(updated_session)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
        "refresh_expires_in_seconds": settings.refresh_token_ttl_days * 24 * 3600,
        "session": await get_user_session_metadata(updated_session),
    }


@router.get("/workspaces", response_model=list[WorkspaceSummary])
async def workspaces(session_info: UserSession = Depends(require_user_session)):
    return await list_user_workspaces(session_info.user_id)


@router.get("/workspace/status", response_model=WorkspaceStatusResponse)
async def workspace_status(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, config = await resolve_workspace_context(session_info, x_workspace_id)
    return await build_workspace_status_response(session_info=session_info, workspace=workspace, config=config)


@router.post("/onboarding/complete")
async def onboarding_complete(session_info: UserSession = Depends(require_user_session)):
    try:
        return await mark_onboarding_completed(actor=session_info)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/workspaces", response_model=WorkspaceSummary)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session_info: UserSession = Depends(require_user_session),
):
    try:
        workspace = await create_workspace_for_user(session_info, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return workspace


@router.get("/users", response_model=list[UserRecordResponse])
async def list_users_endpoint(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    return await list_users_for_workspace(workspace.id)


@router.post("/users", response_model=UserCreateResponse)
async def create_user_endpoint(
    payload: UserCreateRequest,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    try:
        user, temporary_password = await create_user_by_admin(
            actor=session_info,
            workspace_id=workspace.id,
            username=payload.username,
            temporary_password=payload.temporary_password,
            role=payload.role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"user": user, "temporary_password": temporary_password}


@router.get("/invites", response_model=list[InviteRecordResponse])
async def list_invites_endpoint(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    try:
        return await list_invites_for_workspace(actor=session_info, workspace_id=workspace.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/invites", response_model=InviteRecordResponse)
async def create_invite_endpoint(
    payload: InviteCreateRequest,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    try:
        return await create_invite_for_workspace(
            actor=session_info,
            workspace_id=workspace.id,
            email=payload.email,
            role=payload.role,
            expires_in_days=payload.expires_in_days,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/users/{user_id}", response_model=UserRecordResponse)
async def update_user_endpoint(
    user_id: str,
    payload: UserUpdateRequest,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    try:
        return await set_user_active_state(
            actor=session_info,
            workspace_id=workspace.id,
            user_id=user_id,
            is_active=payload.is_active,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/users/{user_id}/reset-password", response_model=UserCreateResponse)
async def reset_user_password_endpoint(
    user_id: str,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_owner_role(workspace)
    try:
        user, temporary_password = await reset_user_password(
            actor=session_info,
            workspace_id=workspace.id,
            user_id=user_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"user": user, "temporary_password": temporary_password}


@router.get("/admin/audit-log")
async def admin_audit_log(
    limit: int = Query(default=25, ge=1, le=100),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)
    return await list_audit_logs(workspace_id=workspace.id, limit=limit)


async def _effective_opportunities() -> list[Opportunity]:
    """Return in-memory state or fall back to DB snapshots (API-only / worker mode)."""
    if _current_opportunities:
        return list(_current_opportunities)
    snapshots = await read_opportunity_snapshots()
    result = []
    for snap in snapshots:
        try:
            result.append(Opportunity(**snap))
        except Exception:
            pass
    return result


def _opportunity_sort_value(opportunity: Opportunity, sort_by: str) -> float:
    if sort_by in {"score", "operational", "comparative"}:
        phase_bonus = {
            "early_breakout": 8.0,
            "continuation": 5.0,
            "accumulation": 2.0,
            "extended": -4.0,
            "distribution_or_profit_zone": -6.0,
            "exhaustion": -8.0,
            "neutral": 0.0,
        }
        range_bonus = {
            "high_quality_reusable_range": 7.0,
            "valid_large_trade": 5.0,
            "valid_medium_trade": 3.0,
            "valid_small_trade": 1.5,
            "weak": -1.0,
            "none": 0.0,
        }
        type_bonus = {"trade": 5.0, "hold": 4.0, "observe": -2.0, "avoid": -12.0}
        phase = opportunity.movement_phase.value if hasattr(opportunity.movement_phase, "value") else opportunity.movement_phase
        late_penalty = -8.0 if opportunity.is_late_entry_risk else 0.0
        return (
            opportunity.score
            + ((opportunity.executability_score or 0.0) * 0.12)
            + ((opportunity.trade_margin_score or 0.0) * 0.08)
            + min(max(opportunity.operational_range_margin_pct or 0.0, 0.0), 20.0) * 0.3
            + phase_bonus.get(str(phase), 0.0)
            + range_bonus.get(opportunity.operational_range_quality or "none", 0.0)
            + type_bonus.get(opportunity.opportunity_type or "observe", 0.0)
            + late_penalty
        )
    sort_keys = {
        "executability": lambda item: item.executability_score if item.executability_score is not None else -1,
        "trade_margin": lambda item: item.trade_margin_score if item.trade_margin_score is not None else -1,
        "net_edge": lambda item: item.estimated_net_trade_edge_pct if item.estimated_net_trade_edge_pct is not None else -999,
        "gap": lambda item: item.cross_exchange_gap_pct,
        "volatility": lambda item: item.volatility_pct,
        "volume": lambda item: item.quote_volume_24h,
        "spread": lambda item: item.spread_pct,
        "price": lambda item: item.last_price,
    }
    return sort_keys.get(sort_by, lambda item: item.score)(opportunity)


def _sort_opportunities(opportunities: list[Opportunity], sort_by: str = "score") -> list[Opportunity]:
    return sorted(
        opportunities,
        key=lambda opportunity: _opportunity_sort_value(opportunity, sort_by),
        reverse=(sort_by != "spread"),
    )


def _summarize_opportunity(opportunity: Opportunity) -> OpportunitySummary:
    return OpportunitySummary(
        id=opportunity.id,
        exchange=opportunity.exchange,
        pair=opportunity.pair,
        score=opportunity.score,
        technical_score=opportunity.technical_score,
        executability_score=opportunity.executability_score,
        executability_band=opportunity.executability_band,
        trade_margin_score=opportunity.trade_margin_score,
        estimated_net_trade_edge_pct=opportunity.estimated_net_trade_edge_pct,
        pipeline_status=opportunity.pipeline_status,
        visibility_reason=opportunity.visibility_reason,
        operationally_visible=opportunity.operationally_visible,
        opportunity_type=opportunity.opportunity_type,
        interesting_signal=opportunity.interesting_signal,
        operable_signal=opportunity.operable_signal,
        volatility_pct=opportunity.volatility_pct,
        volume_24h=opportunity.volume_24h,
        quote_volume_24h=opportunity.quote_volume_24h,
        liquidity_units=opportunity.liquidity_units,
        bid_notional_top_n=opportunity.bid_notional_top_n,
        ask_notional_top_n=opportunity.ask_notional_top_n,
        total_notional_top_n=opportunity.total_notional_top_n,
        spread_pct=opportunity.spread_pct,
        estimated_buy_slippage_bps=opportunity.estimated_buy_slippage_bps,
        estimated_sell_slippage_bps=opportunity.estimated_sell_slippage_bps,
        fillable_notional_within_slippage_cap=opportunity.fillable_notional_within_slippage_cap,
        last_price=opportunity.last_price,
        change_pct=opportunity.change_pct,
        movement_type=opportunity.movement_type,
        movement_regime=opportunity.movement_regime,
        movement_phase=opportunity.movement_phase,
        phase_confidence_score=opportunity.phase_confidence_score,
        phase_reason=opportunity.phase_reason,
        is_late_entry_risk=opportunity.is_late_entry_risk,
        is_profit_zone_candidate=opportunity.is_profit_zone_candidate,
        distance_from_accumulation_zone_pct=opportunity.distance_from_accumulation_zone_pct,
        distance_from_breakout_pct=opportunity.distance_from_breakout_pct,
        operational_range_margin_pct=opportunity.operational_range_margin_pct,
        capital_capacity_estimate_brl=opportunity.capital_capacity_estimate_brl,
        operational_range_quality=opportunity.operational_range_quality,
        alert_moment_type=opportunity.alert_moment_type,
        alert_reason=opportunity.alert_reason,
        alert_worthiness_score=opportunity.alert_worthiness_score,
        alert_trigger_type=opportunity.alert_trigger_type,
        has_actionable_trigger=opportunity.has_actionable_trigger,
        alert_state_key=opportunity.alert_state_key,
        alert_block_reason=opportunity.alert_block_reason,
        detected_at=opportunity.detected_at,
        cross_exchange_gap_pct=opportunity.cross_exchange_gap_pct,
        cross_exchange_reference_exchange=opportunity.cross_exchange_reference_exchange,
        cross_exchange_reference_price=opportunity.cross_exchange_reference_price,
        arbitrage_available=opportunity.arbitrage_available,
        historical_confidence=opportunity.historical_confidence,
    )


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    filtered_opportunities = [
        opportunity
        for opportunity in opps
        if opportunity is not None and is_operationally_visible(opportunity)
    ]
    monitored_pairs = await get_monitored_pair_count(config)
    return build_dashboard_stats(
        opportunities=filtered_opportunities,
        monitored_pairs=monitored_pairs,
        last_scan=_last_scan,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    limit: int = Query(default=50, le=200),
    sort_by: str = "score",
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    visible_opportunities = [
        opportunity
        for opportunity in opps
        if opportunity is not None and is_operationally_visible(opportunity)
    ]
    visible_opportunities = _sort_opportunities(visible_opportunities, sort_by)
    monitored_pairs = await get_monitored_pair_count(config)
    return DashboardResponse(
        stats=build_dashboard_stats(
            opportunities=visible_opportunities,
            monitored_pairs=monitored_pairs,
            last_scan=_last_scan,
        ),
        opportunities=visible_opportunities[:limit],
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    limit: int = Query(default=12, le=50),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    visible_opportunities = [
        opportunity
        for opportunity in opps
        if opportunity is not None and is_operationally_visible(opportunity)
    ]
    shortlist = _sort_opportunities(visible_opportunities, "executability")

    monitored_pairs = await get_monitored_pair_count(config)
    return DashboardSummaryResponse(
        stats=build_dashboard_stats(
            opportunities=visible_opportunities,
            monitored_pairs=monitored_pairs,
            last_scan=_last_scan,
        ),
        shortlist=[_summarize_opportunity(opportunity) for opportunity in shortlist[:limit]],
    )


@router.get("/opportunities", response_model=list[Opportunity])
async def list_opportunities(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    movement_type: str | None = None,
    arbitrage_only: bool = False,
    operable_only: bool = False,
    include_technical: bool = False,
    sort_by: str = "score",
    limit: int = Query(default=50, le=200),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)

    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    visible_opportunities = [opportunity for opportunity in opps if opportunity is not None]

    if not include_technical:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if is_operationally_visible(opportunity)]

    if exchange:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.exchange.value == exchange]
    if pair:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.pair == pair]
    if min_score is not None:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.score >= min_score]
    if movement_type:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.movement_type.value == movement_type]
    if arbitrage_only:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.arbitrage_available]
    if operable_only:
        visible_opportunities = [opportunity for opportunity in visible_opportunities if opportunity.operable_signal]

    visible_opportunities = _sort_opportunities(visible_opportunities, sort_by)
    return visible_opportunities[:limit]


@router.get("/opportunities/active", response_model=list[OpportunitySummary])
async def active_opportunities(
    limit: int = Query(default=20, le=100),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    visible_opportunities = [
        opportunity
        for opportunity in opps
        if opportunity is not None and is_operationally_visible(opportunity)
    ]
    visible_opportunities = _sort_opportunities(visible_opportunities, "score")
    return [_summarize_opportunity(opportunity) for opportunity in visible_opportunities[:limit]]


@router.get("/opportunities/shortlist", response_model=list[OpportunitySummary])
async def opportunities_shortlist(
    limit: int = Query(default=10, le=50),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in base_opportunities]
    shortlisted = [
        opportunity
        for opportunity in opps
        if opportunity is not None and is_operationally_visible(opportunity)
    ]
    shortlisted = _sort_opportunities(shortlisted, "executability")
    return [_summarize_opportunity(opportunity) for opportunity in shortlisted[:limit]]


@router.get("/opportunities/{opp_id}", response_model=Opportunity | None)
async def get_opportunity(
    opp_id: str,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    base_opportunities = await _effective_opportunities()
    for opportunity in base_opportunities:
        if opportunity.id == opp_id:
            return project_workspace_opportunity(opportunity, config)
    return None


@router.post("/signals/feedback", response_model=SignalFeedbackResponse)
async def submit_signal_feedback(
    payload: SignalFeedbackCreate,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    if not payload.signal_id and not payload.opportunity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="signal_id or opportunity_id is required",
        )
    return await create_signal_feedback(
        signal_id=payload.signal_id,
        opportunity_id=payload.opportunity_id,
        user_id=session_info.user_id,
        workspace_id=workspace.id,
        feedback_label=payload.feedback_label,
        feedback_note=payload.feedback_note,
    )


@router.get("/history")
async def history(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    visibility: Literal["operational", "technical", "all"] = "operational",
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    return await get_history(
        limit=limit,
        offset=offset,
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=config,
        visibility=visibility,
    )


@router.get("/history/summary", response_model=list[HistorySummaryRecord])
async def history_summary(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    visibility: Literal["operational", "technical", "all"] = "operational",
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    return await get_history_summary(
        limit=limit,
        offset=offset,
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=config,
        visibility=visibility,
    )


@router.get("/analytics")
async def analytics(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    return await get_filtered_analytics(
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=config,
    )


@router.get("/analytics/operational")
async def operational_analytics(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, config = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)
    return await get_filtered_analytics(
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=config,
    )


@router.get("/pairs/available", response_model=AvailablePairsResponse)
async def available_pairs(
    force_refresh: bool = Query(default=False),
    enabled_exchanges: list[Exchange] | None = Query(default=None),
):
    return await get_available_pairs_catalog(enabled_exchanges=enabled_exchanges, force_refresh=force_refresh)


@router.get("/pairs/diagnostics/{exchange}/{pair:path}", response_model=PairExchangeDiagnosticResponse)
async def pair_diagnostic(exchange: Exchange, pair: str):
    return await get_pair_exchange_diagnostic(exchange, pair)


@router.get("/diagnostics/missed-signal")
async def missed_signal_diagnostic(
    exchange: Exchange,
    pair: str,
    from_time: datetime = Query(alias="from"),
    to_time: datetime = Query(alias="to"),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, config = await resolve_workspace_context(session_info, x_workspace_id)
    catalog_status = None
    try:
        pair_status = await get_pair_exchange_diagnostic(exchange, pair)
        catalog_status = {
            "exchange": exchange.value,
            "pair": pair_status.get("pair", pair.upper().replace("/", "_")),
            "display_name": pair_status.get("display_name"),
            "raw_symbol": pair_status.get("raw_symbol"),
            "exists_in_catalog": pair_status.get("exists_in_catalog"),
            "overall_status": pair_status.get("overall_status"),
            "checked_at": pair_status.get("checked_at"),
            "checks": pair_status.get("checks", []),
            "monitorable": pair_status.get("monitorable"),
            "monitorability_reason": pair_status.get("monitorability_reason"),
        }
    except Exception as exc:
        logger.warning("missed_signal_catalog_status_failed exchange=%s pair=%s error=%s", exchange.value, pair, exc)
        catalog_status = {
            "exchange": exchange.value,
            "pair": pair.upper().replace("/", "_"),
            "overall_status": "error",
            "error": str(exc),
        }

    return await get_missed_signal_diagnostic(
        exchange=exchange.value,
        pair=pair,
        from_time=from_time,
        to_time=to_time,
        workspace_id=workspace.id,
        workspace_config=config,
        catalog_status=catalog_status,
    )


@router.get("/diagnostics/near-misses")
async def near_misses_diagnostic(
    from_time: datetime = Query(alias="from"),
    to_time: datetime = Query(alias="to"),
    exchange: Exchange | None = Query(default=None),
    pair: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    near_misses = await get_near_misses(
        from_time=from_time,
        to_time=to_time,
        exchange=exchange.value if exchange else None,
        pair=pair,
        limit=limit,
    )
    return {
        "workspace_id": workspace.id,
        "from": from_time.isoformat(),
        "to": to_time.isoformat(),
        "exchange": exchange.value if exchange else None,
        "pair": pair.upper().replace("/", "_") if pair else None,
        "count": len(near_misses),
        "near_misses": near_misses,
    }


@router.get("/config", response_model=ConfigResponse)
async def get_config_endpoint(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, config = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)
    return build_config_response(config)


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    update: ConfigUpdate,
    x_workspace_id: str | None = Header(default=None),
    x_config_audit_mode: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, current_config = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)
    update_data = update.model_dump(exclude_none=True)
    updated_config = merge_config_with_sensitive_overrides(current_config, update_data)
    await save_workspace_config(workspace.id, updated_config)
    request_scan_refresh()
    if x_config_audit_mode != "skip":
        await record_audit_event(
            "workspace.config_updated",
            actor_user_id=session_info.user_id,
            actor_username=session_info.username,
            workspace_id=workspace.id,
            details={"updated_fields": sorted(update_data.keys())},
        )
    return build_config_response(updated_config)


@router.post("/config/validate-exchanges", response_model=ExchangeCredentialValidationResponse)
async def validate_exchange_credentials_endpoint(
    payload: ExchangeCredentialValidationRequest,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, current_config = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)
    effective_config = merge_config_with_sensitive_overrides(current_config, payload.model_dump(exclude_none=True))
    results = await validate_exchange_credentials(effective_config)
    await record_audit_event(
        "workspace.exchange_credentials_validated",
        actor_user_id=session_info.user_id,
        actor_username=session_info.username,
        workspace_id=workspace.id,
        details={
            "states": {result.exchange.value: result.state for result in results},
        },
    )
    return {"results": [result.model_dump() for result in results]}


@router.post("/config/telegram/test")
async def test_telegram_endpoint(
    payload: TelegramTestRequest,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, current_config = await resolve_workspace_context(session_info, x_workspace_id)
    require_workspace_admin_role(workspace)

    effective_token = (payload.telegram_bot_token or "").strip() or current_config.telegram_bot_token
    effective_chat_id = (payload.telegram_chat_id or "").strip() or current_config.telegram_chat_id

    try:
        await send_telegram_test_message(
            token=effective_token,
            chat_id=effective_chat_id,
            workspace_name=workspace.name,
            actor_username=session_info.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("telegram_test_failed error=%s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to deliver Telegram test message",
        ) from exc

    return {"delivered": True}


@router.get("/health")
async def health():
    runtime = scan_monitor.snapshot()
    scanner_state = await get_scanner_runtime_state()
    has_local_scanner = _last_scan is not None
    return {
        "status": "ok",
        "mode": "scanner" if has_local_scanner else "api_only",
        "last_scan": _last_scan.isoformat() if _last_scan else None,
        "opportunities_count": len(_current_opportunities),
        "scanner": runtime,
        "scanner_state": scanner_state,
        "websocket_connections": manager.connection_count,
        "scan_configured_exchanges": [exchange.value for exchange in _scan_config.enabled_exchanges],
    }
