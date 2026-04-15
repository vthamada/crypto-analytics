from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.api.websocket import manager
from app.config import settings
from app.models.schemas import (
    AppConfig,
    DashboardStats,
    Exchange,
    FilterThresholds,
    Opportunity,
    ScoreWeights,
    UserSessionResponse,
    WorkspaceSummary,
)
from app.services.auth import (
    UserSession,
    authenticate_admin_credentials,
    change_admin_password,
    create_workspace_for_user,
    ensure_admin_bootstrap,
    get_user_session_metadata,
    get_workspace_for_user,
    issue_access_token,
    legacy_admin_session,
    list_audit_logs,
    list_user_workspaces,
    record_audit_event,
    validate_legacy_admin_token,
    verify_access_token,
)
from app.services.monitoring import scan_monitor
from app.services.persistence import (
    DEFAULT_WORKSPACE_ID,
    get_filtered_analytics,
    get_history,
    get_workspace_score,
    load_config,
    load_workspace_config,
    opportunity_matches_config,
    save_workspace_config,
)

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
        if workspace_id and workspace_id != DEFAULT_WORKSPACE_ID:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace auth required")
        config = await load_workspace_config(DEFAULT_WORKSPACE_ID) or await load_config() or AppConfig()
        return (
            WorkspaceSummary(
                id=DEFAULT_WORKSPACE_ID,
                slug="default",
                name="Default Workspace",
                role="viewer",
                is_active=True,
            ),
            config,
        )

    workspaces = await list_user_workspaces(session_info.user_id)
    if not workspaces:
        if session_info.auth_mode == "legacy_token":
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
        config = await load_workspace_config(DEFAULT_WORKSPACE_ID) or await load_config() or AppConfig()
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
    return Opportunity(**data)


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class WorkspaceCreateRequest(BaseModel):
    name: str


class ConfigUpdate(BaseModel):
    thresholds: FilterThresholds | None = None
    weights: ScoreWeights | None = None
    enabled_exchanges: list[Exchange] | None = None
    enabled_pairs: list[str] | None = None
    scan_interval_seconds: int | None = None
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    novadax_api_key: str | None = None
    novadax_api_secret: str | None = None
    mb_api_key: str | None = None
    mb_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None


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

    token = issue_access_token(session_info)
    await record_audit_event(
        "auth.login",
        actor_user_id=session_info.user_id,
        actor_username=session_info.username,
        details={"auth_mode": session_info.auth_mode},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
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

    token = issue_access_token(updated_session)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_ttl_minutes * 60,
        "session": await get_user_session_metadata(updated_session),
    }


@router.get("/workspaces", response_model=list[WorkspaceSummary])
async def workspaces(session_info: UserSession = Depends(require_user_session)):
    return await list_user_workspaces(session_info.user_id)


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


@router.get("/admin/audit-log")
async def admin_audit_log(
    limit: int = Query(default=25, ge=1, le=100),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, _ = await resolve_workspace_context(session_info, x_workspace_id)
    return await list_audit_logs(workspace_id=workspace.id, limit=limit)


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession | None = Depends(get_optional_user_session),
):
    workspace, config = await resolve_workspace_context(session_info, x_workspace_id)
    opps = [project_workspace_opportunity(opportunity, config) for opportunity in _current_opportunities]
    filtered_opportunities = [opportunity for opportunity in opps if opportunity is not None]
    exchanges_online = len({opportunity.exchange for opportunity in filtered_opportunities})
    return DashboardStats(
        total_opportunities=len(filtered_opportunities),
        active_opportunities=len([opportunity for opportunity in filtered_opportunities if opportunity.score >= 40]),
        monitored_pairs=len(config.enabled_pairs),
        total_volume_24h=sum(opportunity.quote_volume_24h for opportunity in filtered_opportunities),
        best_score=max((opportunity.score for opportunity in filtered_opportunities), default=0),
        exchanges_online=exchanges_online,
        arbitrage_opportunities=len([opportunity for opportunity in filtered_opportunities if opportunity.arbitrage_available]),
        last_scan=_last_scan,
    )


@router.get("/opportunities", response_model=list[Opportunity])
async def list_opportunities(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    movement_type: str | None = None,
    arbitrage_only: bool = False,
    sort_by: str = "score",
    limit: int = Query(default=50, le=200),
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession | None = Depends(get_optional_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)

    opps = [project_workspace_opportunity(opportunity, config) for opportunity in _current_opportunities]
    visible_opportunities = [opportunity for opportunity in opps if opportunity is not None]

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

    sort_keys = {
        "score": lambda opportunity: opportunity.score,
        "gap": lambda opportunity: opportunity.cross_exchange_gap_pct,
        "volatility": lambda opportunity: opportunity.volatility_pct,
        "volume": lambda opportunity: opportunity.quote_volume_24h,
        "spread": lambda opportunity: opportunity.spread_pct,
        "price": lambda opportunity: opportunity.last_price,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["score"])
    visible_opportunities.sort(key=key_fn, reverse=(sort_by != "spread"))
    return visible_opportunities[:limit]


@router.get("/opportunities/{opp_id}", response_model=Opportunity | None)
async def get_opportunity(
    opp_id: str,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession | None = Depends(get_optional_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    for opportunity in _current_opportunities:
        if opportunity.id == opp_id:
            return project_workspace_opportunity(opportunity, config)
    return None


@router.get("/history")
async def history(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession | None = Depends(get_optional_user_session),
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
    )


@router.get("/analytics")
async def analytics(
    exchange: str | None = None,
    pair: str | None = None,
    min_score: float | None = None,
    hours: int | None = None,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession | None = Depends(get_optional_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    return await get_filtered_analytics(
        exchange=exchange,
        pair=pair,
        min_score=min_score,
        hours=hours,
        workspace_config=config,
    )


@router.get("/config", response_model=AppConfig)
async def get_config_endpoint(
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    _, config = await resolve_workspace_context(session_info, x_workspace_id)
    return sanitize_config(config)


@router.put("/config", response_model=AppConfig)
async def update_config(
    update: ConfigUpdate,
    x_workspace_id: str | None = Header(default=None),
    session_info: UserSession = Depends(require_user_session),
):
    workspace, current_config = await resolve_workspace_context(session_info, x_workspace_id)
    data = current_config.model_dump()
    update_data = update.model_dump(exclude_none=True)

    for field in _SENSITIVE_CONFIG_FIELDS:
        if update_data.get(field, None) == "":
            update_data.pop(field)

    data.update(update_data)
    updated_config = AppConfig(**data)
    await save_workspace_config(workspace.id, updated_config)
    await record_audit_event(
        "workspace.config_updated",
        actor_user_id=session_info.user_id,
        actor_username=session_info.username,
        workspace_id=workspace.id,
        details={"updated_fields": sorted(update_data.keys())},
    )
    return sanitize_config(updated_config)


@router.get("/health")
async def health():
    runtime = scan_monitor.snapshot()
    return {
        "status": "ok",
        "last_scan": _last_scan.isoformat() if _last_scan else None,
        "opportunities_count": len(_current_opportunities),
        "scanner": runtime,
        "websocket_connections": manager.connection_count,
        "scan_configured_exchanges": [exchange.value for exchange in _scan_config.enabled_exchanges],
    }
