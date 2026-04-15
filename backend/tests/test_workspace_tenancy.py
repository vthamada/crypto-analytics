from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import routes
from app.models.database import Base
from app.models.schemas import AppConfig, Exchange, MovementType, Opportunity, ScoreWeights
from app.services import auth, persistence


def test_workspace_configs_are_isolated_per_tenant(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"workspace-config-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(auth, "async_session", session_factory)
        monkeypatch.setattr(persistence, "async_session", session_factory)
        monkeypatch.setattr(auth.settings, "admin_username", "admin")
        monkeypatch.setattr(auth.settings, "admin_password", "initial-secret")
        monkeypatch.setattr(auth.settings, "auth_secret_key", "signing-key")
        monkeypatch.setattr(auth.settings, "admin_token", "")

        await auth.ensure_admin_bootstrap()
        admin_session = await auth.authenticate_admin_credentials("admin", "initial-secret")
        assert admin_session is not None

        admin_workspaces = await auth.list_user_workspaces(admin_session.user_id)
        default_workspace = admin_workspaces[0]
        second_workspace = await auth.create_workspace_for_user(admin_session, "Swing Desk")

        await persistence.save_workspace_config(
            default_workspace.id,
            AppConfig(enabled_pairs=["BTC_BRL"], enabled_exchanges=[Exchange.BINANCE], scan_interval_seconds=15),
        )
        await persistence.save_workspace_config(
            second_workspace.id,
            AppConfig(enabled_pairs=["ETH_BRL"], enabled_exchanges=[Exchange.NOVADAX], scan_interval_seconds=45),
        )

        default_config = await persistence.load_workspace_config(default_workspace.id)
        swing_config = await persistence.load_workspace_config(second_workspace.id)

        assert default_config is not None
        assert swing_config is not None
        assert default_config.enabled_pairs == ["BTC_BRL"]
        assert swing_config.enabled_pairs == ["ETH_BRL"]
        assert default_config.enabled_exchanges == [Exchange.BINANCE]
        assert swing_config.enabled_exchanges == [Exchange.NOVADAX]
        assert default_config.scan_interval_seconds == 15
        assert swing_config.scan_interval_seconds == 45

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_membership_scope_blocks_other_workspaces(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"workspace-membership-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(auth, "async_session", session_factory)
        monkeypatch.setattr(auth.settings, "admin_username", "admin")
        monkeypatch.setattr(auth.settings, "admin_password", "initial-secret")
        monkeypatch.setattr(auth.settings, "auth_secret_key", "signing-key")
        monkeypatch.setattr(auth.settings, "admin_token", "")

        await auth.ensure_admin_bootstrap()
        admin_session = await auth.authenticate_admin_credentials("admin", "initial-secret")
        assert admin_session is not None

        admin_workspaces = await auth.list_user_workspaces(admin_session.user_id)
        default_workspace = admin_workspaces[0]
        second_workspace = await auth.create_workspace_for_user(admin_session, "Research Desk")
        created_user, temporary_password = await auth.create_user_by_admin(
            actor=admin_session,
            workspace_id=second_workspace.id,
            username="analista",
            role="member",
        )

        member_session = await auth.authenticate_admin_credentials("analista", temporary_password)
        assert member_session is not None

        member_workspaces = await auth.list_user_workspaces(member_session.user_id)
        denied_workspace = await auth.get_workspace_for_user(member_session.user_id, default_workspace.id)

        assert [workspace.id for workspace in member_workspaces] == [second_workspace.id]
        assert denied_workspace is None
        assert created_user["username"] == "analista"

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_workspace_projection_uses_workspace_specific_weights_and_filters():
    opportunity = Opportunity(
        id="opp-1",
        exchange=Exchange.BINANCE,
        pair="BTC_BRL",
        score=50,
        volatility_pct=5,
        volume_24h=1000,
        quote_volume_24h=150000,
        liquidity_units=8000,
        spread_pct=0.2,
        movement_type=MovementType.STRONG_RANGE,
        last_price=100000,
        change_pct=4,
        volatility_score=0.9,
        volume_score=0.3,
        liquidity_score=0.4,
        spread_score=0.1,
        repetition_score=0.2,
        historical_confidence=1.0,
    )

    volatility_workspace = AppConfig(
        enabled_pairs=["BTC_BRL"],
        enabled_exchanges=[Exchange.BINANCE],
        weights=ScoreWeights(volatility=1.0, volume=0.0, liquidity=0.0, spread=0.0, repetition=0.0),
    )
    spread_workspace = AppConfig(
        enabled_pairs=["BTC_BRL"],
        enabled_exchanges=[Exchange.BINANCE],
        weights=ScoreWeights(volatility=0.0, volume=0.0, liquidity=0.0, spread=1.0, repetition=0.0),
    )
    filtered_workspace = AppConfig(
        enabled_pairs=["ETH_BRL"],
        enabled_exchanges=[Exchange.BINANCE],
    )

    projected_volatility = routes.project_workspace_opportunity(opportunity, volatility_workspace)
    projected_spread = routes.project_workspace_opportunity(opportunity, spread_workspace)
    projected_filtered = routes.project_workspace_opportunity(opportunity, filtered_workspace)

    assert projected_volatility is not None
    assert projected_spread is not None
    assert projected_filtered is None
    assert projected_volatility.score > projected_spread.score