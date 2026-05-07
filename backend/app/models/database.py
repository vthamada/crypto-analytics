from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.models.schemas import Exchange, MovementType


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    # Database columns are stored as TIMESTAMP WITHOUT TIME ZONE in Postgres.
    # Keep values in UTC, but strip tzinfo so asyncpg can bind them safely.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_db_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class OpportunityRecord(Base):
    __tablename__ = "opportunities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exchange = Column(String, nullable=False, index=True)
    pair = Column(String, nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)
    volatility_pct = Column(Float, nullable=False)
    volume_24h = Column(Float, nullable=False)
    quote_volume_24h = Column(Float, nullable=False)
    liquidity_units = Column(Float, nullable=False)
    spread_pct = Column(Float, nullable=False)
    movement_type = Column(String, nullable=False)
    last_price = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    duration_minutes = Column(Float, default=0.0)
    cross_exchange_gap_pct = Column(Float, default=0.0)
    cross_exchange_reference_exchange = Column(String, nullable=True)
    cross_exchange_reference_price = Column(Float, nullable=True)
    arbitrage_available = Column(Boolean, default=False, index=True)
    historical_confidence = Column(Float, default=1.0)
    volatility_score = Column(Float, default=0.0)
    volume_score = Column(Float, default=0.0)
    liquidity_score = Column(Float, default=0.0)
    spread_score = Column(Float, default=0.0)
    repetition_score = Column(Float, default=0.0)
    movement_multiplier = Column(Float, default=1.0)
    technical_score = Column(Float, nullable=True)
    score_version = Column(String, nullable=True, default="v1")
    executability_version = Column(String, nullable=True, default="v1")
    movement_version = Column(String, nullable=True, default="v1")
    profile_version = Column(String, nullable=True, default="v1")
    reweighting_version = Column(String, nullable=True, default="v1")
    technical_signal_id = Column(String, nullable=True)
    semantic_signal_key = Column(String, nullable=True, index=True)
    executability_score = Column(Float, nullable=True)
    executability_band = Column(String, nullable=True)
    interesting_signal = Column(Boolean, nullable=True)
    operable_signal = Column(Boolean, nullable=True)
    estimated_trade_margin_pct = Column(Float, nullable=True)
    operational_friction_pct = Column(Float, nullable=True)
    estimated_net_trade_edge_pct = Column(Float, nullable=True)
    trade_margin_score = Column(Float, nullable=True)
    opportunity_type = Column(String, nullable=True, index=True)
    bid_notional_top_n = Column(Float, nullable=True)
    ask_notional_top_n = Column(Float, nullable=True)
    total_notional_top_n = Column(Float, nullable=True)
    estimated_buy_slippage_bps = Column(Float, nullable=True)
    estimated_sell_slippage_bps = Column(Float, nullable=True)
    fillable_notional_within_slippage_cap = Column(Float, nullable=True)
    baseline_order_notional_brl = Column(Float, nullable=True)
    movement_regime = Column(String, nullable=True)
    movement_phase = Column(String, nullable=True)
    phase_confidence_score = Column(Float, nullable=True)
    phase_reason = Column(String, nullable=True)
    is_late_entry_risk = Column(Boolean, default=False)
    is_profit_zone_candidate = Column(Boolean, default=False)
    distance_from_accumulation_zone_pct = Column(Float, nullable=True)
    distance_from_breakout_pct = Column(Float, nullable=True)
    operational_buy_zone_low = Column(Float, nullable=True)
    operational_buy_zone_high = Column(Float, nullable=True)
    operational_sell_zone_low = Column(Float, nullable=True)
    operational_sell_zone_high = Column(Float, nullable=True)
    operational_range_margin_pct = Column(Float, nullable=True)
    range_reuse_count = Column(Integer, default=0)
    range_reliability_score = Column(Float, nullable=True)
    zone_liquidity_score = Column(Float, nullable=True)
    capital_capacity_estimate_brl = Column(Float, nullable=True)
    operational_range_quality = Column(String, nullable=True)
    alert_moment_type = Column(String, nullable=True)
    alert_reason = Column(String, nullable=True)
    movement_persistence_score = Column(Float, nullable=True)


class ConfigRecord(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AdminUserRecord(Base):
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    token_version = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    password_updated_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class OrganizationRecord(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    plan = Column(String, nullable=False, default="trial")
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=False, default="trialing")
    trial_ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class UserRecord(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="member", index=True)
    organization_id = Column(String, nullable=True, index=True)
    token_version = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_by_user_id = Column(String, nullable=True, index=True)
    onboarding_completed_at = Column(DateTime, nullable=True)
    password_updated_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    owner_user_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class WorkspaceMembershipRecord(Base):
    __tablename__ = "workspace_memberships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="member", index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class WorkspaceConfigRecord(Base):
    __tablename__ = "workspace_configs"

    workspace_id = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class InviteRecord(Base):
    __tablename__ = "invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, index=True)
    organization_id = Column(String, nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="member")
    created_by_user_id = Column(String, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id = Column(String, nullable=True, index=True)
    actor_username = Column(String, nullable=True, index=True)
    workspace_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="success")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class ScannerRuntimeStateRecord(Base):
    __tablename__ = "scanner_runtime_state"

    id = Column(String, primary_key=True, default="singleton")
    last_cycle_started_at = Column(DateTime, nullable=True)
    last_cycle_completed_at = Column(DateTime, nullable=True)
    last_cycle_duration_ms = Column(Float, nullable=True)
    last_cycle_error = Column(Text, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    opportunities_count = Column(Integer, nullable=False, default=0)
    score_version = Column(String, nullable=False, default="v1")
    executability_version = Column(String, nullable=False, default="v1")
    movement_version = Column(String, nullable=False, default="v1")
    profile_version = Column(String, nullable=False, default="v1")
    last_scan_diagnostics = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ScannerCycleAuditRecord(Base):
    __tablename__ = "scanner_cycle_audits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="completed", index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    duration_ms = Column(Float, nullable=True)
    total_pairs = Column(Integer, nullable=False, default=0)
    brl_pairs = Column(Integer, nullable=False, default=0)
    light_candidates = Column(Integer, nullable=False, default=0)
    deep_candidates = Column(Integer, nullable=False, default=0)
    deep_completed = Column(Integer, nullable=False, default=0)
    signals_created = Column(Integer, nullable=False, default=0)
    shortlist_count = Column(Integer, nullable=False, default=0)
    alerts_created = Column(Integer, nullable=False, default=0)
    alerts_sent = Column(Integer, nullable=False, default=0)
    provider_errors = Column(Integer, nullable=False, default=0)
    discard_reasons = Column(Text, nullable=True)
    block_reasons = Column(Text, nullable=True)
    diagnostics = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class SignalPipelineEventRecord(Base):
    __tablename__ = "signal_pipeline_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cycle_id = Column(String, nullable=False, index=True)
    exchange = Column(String, nullable=True, index=True)
    pair = Column(String, nullable=True, index=True)
    stage = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    reason = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, default="scanner")
    workspace_id = Column(String, nullable=True, index=True)
    technical_signal_id = Column(String, nullable=True, index=True)
    opportunity_id = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class OpportunitySnapshotRecord(Base):
    __tablename__ = "opportunity_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exchange = Column(String, nullable=False, index=True)
    pair = Column(String, nullable=False, index=True)
    score = Column(Float, nullable=False)
    technical_score = Column(Float, nullable=False)
    score_version = Column(String, nullable=False, default="v1")
    executability_version = Column(String, nullable=False, default="v1")
    movement_version = Column(String, nullable=False, default="v1")
    profile_version = Column(String, nullable=False, default="v1")
    reweighting_version = Column(String, nullable=False, default="v1")
    volatility_pct = Column(Float, nullable=False)
    volume_24h = Column(Float, nullable=False)
    quote_volume_24h = Column(Float, nullable=False)
    liquidity_units = Column(Float, nullable=False)
    bid_notional_top_n = Column(Float, nullable=True)
    ask_notional_top_n = Column(Float, nullable=True)
    total_notional_top_n = Column(Float, nullable=True)
    spread_pct = Column(Float, nullable=False)
    executability_score = Column(Float, nullable=True)
    executability_band = Column(String, nullable=True)
    interesting_signal = Column(Boolean, nullable=True)
    operable_signal = Column(Boolean, nullable=True)
    estimated_trade_margin_pct = Column(Float, nullable=True)
    operational_friction_pct = Column(Float, nullable=True)
    estimated_net_trade_edge_pct = Column(Float, nullable=True)
    trade_margin_score = Column(Float, nullable=True)
    opportunity_type = Column(String, nullable=True, index=True)
    estimated_buy_slippage_bps = Column(Float, nullable=True)
    estimated_sell_slippage_bps = Column(Float, nullable=True)
    fillable_notional_within_slippage_cap = Column(Float, nullable=True)
    baseline_order_notional_brl = Column(Float, nullable=True)
    movement_type = Column(String, nullable=False)
    movement_regime = Column(String, nullable=True)
    movement_phase = Column(String, nullable=True)
    phase_confidence_score = Column(Float, nullable=True)
    phase_reason = Column(String, nullable=True)
    is_late_entry_risk = Column(Boolean, default=False)
    is_profit_zone_candidate = Column(Boolean, default=False)
    distance_from_accumulation_zone_pct = Column(Float, nullable=True)
    distance_from_breakout_pct = Column(Float, nullable=True)
    operational_buy_zone_low = Column(Float, nullable=True)
    operational_buy_zone_high = Column(Float, nullable=True)
    operational_sell_zone_low = Column(Float, nullable=True)
    operational_sell_zone_high = Column(Float, nullable=True)
    operational_range_margin_pct = Column(Float, nullable=True)
    range_reuse_count = Column(Integer, default=0)
    range_reliability_score = Column(Float, nullable=True)
    zone_liquidity_score = Column(Float, nullable=True)
    capital_capacity_estimate_brl = Column(Float, nullable=True)
    operational_range_quality = Column(String, nullable=True)
    alert_moment_type = Column(String, nullable=True)
    alert_reason = Column(String, nullable=True)
    movement_persistence_score = Column(Float, nullable=True)
    last_price = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=utcnow)
    historical_confidence = Column(Float, default=1.0)
    volatility_score = Column(Float, default=0.0)
    volume_score = Column(Float, default=0.0)
    liquidity_score = Column(Float, default=0.0)
    spread_score = Column(Float, default=0.0)
    repetition_score = Column(Float, default=0.0)
    movement_multiplier = Column(Float, default=1.0)
    cross_exchange_gap_pct = Column(Float, default=0.0)
    cross_exchange_reference_exchange = Column(String, nullable=True)
    cross_exchange_reference_price = Column(Float, nullable=True)
    arbitrage_available = Column(Boolean, default=False)
    snapshot_cycle_id = Column(String, nullable=False, index=True)


class TechnicalSignalRecord(Base):
    __tablename__ = "technical_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exchange = Column(String, nullable=False, index=True)
    pair = Column(String, nullable=False, index=True)
    technical_score = Column(Float, nullable=False, index=True)
    score_version = Column(String, nullable=False, default="v1")
    executability_version = Column(String, nullable=False, default="v1")
    movement_version = Column(String, nullable=False, default="v1")
    profile_version = Column(String, nullable=False, default="v1")
    reweighting_version = Column(String, nullable=False, default="v1")
    volatility_pct = Column(Float, nullable=False)
    volatility_score = Column(Float, default=0.0)
    volume_24h = Column(Float, nullable=False)
    quote_volume_24h = Column(Float, nullable=False)
    volume_score = Column(Float, default=0.0)
    liquidity_units = Column(Float, nullable=False)
    liquidity_score = Column(Float, default=0.0)
    spread_pct = Column(Float, nullable=False)
    spread_score = Column(Float, default=0.0)
    repetition_score = Column(Float, default=0.0)
    movement_type = Column(String, nullable=False)
    movement_regime = Column(String, nullable=True)
    movement_phase = Column(String, nullable=True)
    phase_confidence_score = Column(Float, nullable=True)
    phase_reason = Column(String, nullable=True)
    is_late_entry_risk = Column(Boolean, default=False)
    is_profit_zone_candidate = Column(Boolean, default=False)
    distance_from_accumulation_zone_pct = Column(Float, nullable=True)
    distance_from_breakout_pct = Column(Float, nullable=True)
    operational_range_margin_pct = Column(Float, nullable=True)
    operational_range_quality = Column(String, nullable=True)
    alert_moment_type = Column(String, nullable=True)
    alert_reason = Column(String, nullable=True)
    movement_multiplier = Column(Float, default=1.0)
    last_price = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)
    historical_confidence = Column(Float, default=1.0)
    cross_exchange_gap_pct = Column(Float, default=0.0)
    cross_exchange_reference_exchange = Column(String, nullable=True)
    cross_exchange_reference_price = Column(Float, nullable=True)
    arbitrage_available = Column(Boolean, default=False, index=True)
    semantic_signal_key = Column(String, nullable=True, index=True)
    detected_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class WorkspaceSignalProjectionRecord(Base):
    __tablename__ = "workspace_signal_projections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String, nullable=False, index=True)
    technical_signal_id = Column(String, nullable=False, index=True)
    workspace_score = Column(Float, nullable=False)
    score_version = Column(String, nullable=False, default="v1")
    executability_version = Column(String, nullable=False, default="v1")
    movement_version = Column(String, nullable=False, default="v1")
    profile_version = Column(String, nullable=False, default="v1")
    reweighting_version = Column(String, nullable=False, default="v1")
    visible = Column(Boolean, nullable=False, default=True)
    alert_eligible = Column(Boolean, nullable=False, default=False)
    projection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class RawMarketObservationRecord(Base):
    __tablename__ = "raw_market_observations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    observation_cycle_id = Column(String, nullable=False, index=True)
    exchange = Column(String, nullable=False, index=True)
    pair = Column(String, nullable=False, index=True)
    semantic_signal_key = Column(String, nullable=True, index=True)
    movement_type = Column(String, nullable=False)
    movement_regime = Column(String, nullable=True)
    movement_phase = Column(String, nullable=True)
    phase_confidence_score = Column(Float, nullable=True)
    phase_reason = Column(String, nullable=True)
    is_late_entry_risk = Column(Boolean, default=False)
    is_profit_zone_candidate = Column(Boolean, default=False)
    distance_from_accumulation_zone_pct = Column(Float, nullable=True)
    distance_from_breakout_pct = Column(Float, nullable=True)
    operational_range_margin_pct = Column(Float, nullable=True)
    operational_range_quality = Column(String, nullable=True)
    alert_moment_type = Column(String, nullable=True)
    alert_reason = Column(String, nullable=True)
    last_price = Column(Float, nullable=False)
    quote_volume_24h = Column(Float, nullable=False)
    liquidity_units = Column(Float, nullable=False)
    spread_pct = Column(Float, nullable=False)
    bid_notional_top_n = Column(Float, nullable=True)
    ask_notional_top_n = Column(Float, nullable=True)
    total_notional_top_n = Column(Float, nullable=True)
    detected_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class SignalOutcomeRecord(Base):
    __tablename__ = "signal_outcomes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    technical_signal_id = Column(String, nullable=False, index=True)
    exchange = Column(String, nullable=False)
    pair = Column(String, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    price_after_5m = Column(Float, nullable=True)
    price_after_15m = Column(Float, nullable=True)
    price_after_1h = Column(Float, nullable=True)
    price_after_4h = Column(Float, nullable=True)
    price_after_24h = Column(Float, nullable=True)
    max_price_1h = Column(Float, nullable=True)
    min_price_1h = Column(Float, nullable=True)
    max_price_after_signal = Column(Float, nullable=True)
    min_price_after_signal = Column(Float, nullable=True)
    outcome_pct_5m = Column(Float, nullable=True)
    outcome_pct_15m = Column(Float, nullable=True)
    outcome_pct_1h = Column(Float, nullable=True)
    outcome_pct_4h = Column(Float, nullable=True)
    outcome_pct_24h = Column(Float, nullable=True)
    max_favorable_excursion_pct = Column(Float, nullable=True)
    max_adverse_excursion_pct = Column(Float, nullable=True)
    volume_after_signal = Column(Float, nullable=True)
    movement_continued = Column(Boolean, nullable=True)
    breakout_confirmed = Column(Boolean, nullable=True)
    late_signal_detected = Column(Boolean, nullable=True)
    outcome_label = Column(String, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    signal_detected_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class SignalFeedbackRecord(Base):
    __tablename__ = "signal_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id = Column(String, nullable=True, index=True)
    opportunity_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    workspace_id = Column(String, nullable=True, index=True)
    feedback_label = Column(String, nullable=False, index=True)
    feedback_note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)


class RepetitionCountRecord(Base):
    __tablename__ = "repetition_counts"

    id = Column(String, primary_key=True)  # "exchange:pair"
    exchange = Column(String, nullable=False)
    pair = Column(String, nullable=False)
    count = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


# Engine setup
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"statement_cache_size": 0},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_sync_database_url() -> str:
    sync_url = (
        settings.database_url
        .replace("sqlite+aiosqlite://", "sqlite://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )
    return sync_url.replace("ssl=require", "sslmode=require")


def get_alembic_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    config.set_main_option("sqlalchemy.url", get_sync_database_url())
    return config


def run_migrations(command_name: str = "upgrade") -> None:
    config = get_alembic_config()
    if command_name == "stamp":
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")


async def init_db() -> None:
    async with engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

    if not table_names or "alembic_version" in table_names:
        run_migrations("upgrade")
        await ensure_schema_compatibility()
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema_compatibility()
    run_migrations("stamp")


async def ensure_schema_compatibility() -> None:
    opportunity_columns = {
        "cross_exchange_gap_pct": "FLOAT DEFAULT 0.0",
        "cross_exchange_reference_exchange": "VARCHAR",
        "cross_exchange_reference_price": "FLOAT",
        "arbitrage_available": "BOOLEAN DEFAULT FALSE",
        "historical_confidence": "FLOAT DEFAULT 1.0",
        "volatility_score": "FLOAT DEFAULT 0.0",
        "volume_score": "FLOAT DEFAULT 0.0",
        "liquidity_score": "FLOAT DEFAULT 0.0",
        "spread_score": "FLOAT DEFAULT 0.0",
        "repetition_score": "FLOAT DEFAULT 0.0",
        "movement_multiplier": "FLOAT DEFAULT 1.0",
        "technical_score": "FLOAT",
        "score_version": "VARCHAR DEFAULT 'v1'",
        "executability_version": "VARCHAR DEFAULT 'v1'",
        "movement_version": "VARCHAR DEFAULT 'v1'",
        "profile_version": "VARCHAR DEFAULT 'v1'",
        "reweighting_version": "VARCHAR DEFAULT 'v1'",
        "technical_signal_id": "VARCHAR",
        "semantic_signal_key": "VARCHAR",
        "executability_score": "FLOAT",
        "executability_band": "VARCHAR",
        "interesting_signal": "BOOLEAN",
        "operable_signal": "BOOLEAN",
        "estimated_trade_margin_pct": "FLOAT",
        "operational_friction_pct": "FLOAT",
        "estimated_net_trade_edge_pct": "FLOAT",
        "trade_margin_score": "FLOAT",
        "opportunity_type": "VARCHAR",
        "bid_notional_top_n": "FLOAT",
        "ask_notional_top_n": "FLOAT",
        "total_notional_top_n": "FLOAT",
        "estimated_buy_slippage_bps": "FLOAT",
        "estimated_sell_slippage_bps": "FLOAT",
        "fillable_notional_within_slippage_cap": "FLOAT",
        "baseline_order_notional_brl": "FLOAT",
        "movement_regime": "VARCHAR",
        "movement_phase": "VARCHAR",
        "phase_confidence_score": "FLOAT",
        "phase_reason": "VARCHAR",
        "is_late_entry_risk": "BOOLEAN DEFAULT FALSE",
        "is_profit_zone_candidate": "BOOLEAN DEFAULT FALSE",
        "distance_from_accumulation_zone_pct": "FLOAT",
        "distance_from_breakout_pct": "FLOAT",
        "operational_buy_zone_low": "FLOAT",
        "operational_buy_zone_high": "FLOAT",
        "operational_sell_zone_low": "FLOAT",
        "operational_sell_zone_high": "FLOAT",
        "operational_range_margin_pct": "FLOAT",
        "range_reuse_count": "INTEGER DEFAULT 0",
        "range_reliability_score": "FLOAT",
        "zone_liquidity_score": "FLOAT",
        "capital_capacity_estimate_brl": "FLOAT",
        "operational_range_quality": "VARCHAR",
        "alert_moment_type": "VARCHAR",
        "alert_reason": "VARCHAR",
        "movement_persistence_score": "FLOAT",
    }

    scanner_runtime_columns = {
        "score_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "executability_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "movement_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "profile_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "reweighting_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "last_scan_diagnostics": "TEXT",
    }

    snapshot_columns = {
        "score_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "executability_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "movement_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "profile_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "reweighting_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "bid_notional_top_n": "FLOAT",
        "ask_notional_top_n": "FLOAT",
        "total_notional_top_n": "FLOAT",
        "executability_score": "FLOAT",
        "executability_band": "VARCHAR",
        "interesting_signal": "BOOLEAN",
        "operable_signal": "BOOLEAN",
        "estimated_trade_margin_pct": "FLOAT",
        "operational_friction_pct": "FLOAT",
        "estimated_net_trade_edge_pct": "FLOAT",
        "trade_margin_score": "FLOAT",
        "opportunity_type": "VARCHAR",
        "estimated_buy_slippage_bps": "FLOAT",
        "estimated_sell_slippage_bps": "FLOAT",
        "fillable_notional_within_slippage_cap": "FLOAT",
        "baseline_order_notional_brl": "FLOAT",
        "movement_regime": "VARCHAR",
        "movement_phase": "VARCHAR",
        "phase_confidence_score": "FLOAT",
        "phase_reason": "VARCHAR",
        "is_late_entry_risk": "BOOLEAN DEFAULT FALSE",
        "is_profit_zone_candidate": "BOOLEAN DEFAULT FALSE",
        "distance_from_accumulation_zone_pct": "FLOAT",
        "distance_from_breakout_pct": "FLOAT",
        "operational_buy_zone_low": "FLOAT",
        "operational_buy_zone_high": "FLOAT",
        "operational_sell_zone_low": "FLOAT",
        "operational_sell_zone_high": "FLOAT",
        "operational_range_margin_pct": "FLOAT",
        "range_reuse_count": "INTEGER DEFAULT 0",
        "range_reliability_score": "FLOAT",
        "zone_liquidity_score": "FLOAT",
        "capital_capacity_estimate_brl": "FLOAT",
        "operational_range_quality": "VARCHAR",
        "alert_moment_type": "VARCHAR",
        "alert_reason": "VARCHAR",
        "movement_persistence_score": "FLOAT",
    }

    technical_signal_columns = {
        "score_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "executability_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "movement_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "profile_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "reweighting_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "movement_regime": "VARCHAR",
        "movement_phase": "VARCHAR",
        "phase_confidence_score": "FLOAT",
        "phase_reason": "VARCHAR",
        "is_late_entry_risk": "BOOLEAN DEFAULT FALSE",
        "is_profit_zone_candidate": "BOOLEAN DEFAULT FALSE",
        "distance_from_accumulation_zone_pct": "FLOAT",
        "distance_from_breakout_pct": "FLOAT",
        "operational_range_margin_pct": "FLOAT",
        "operational_range_quality": "VARCHAR",
        "alert_moment_type": "VARCHAR",
        "alert_reason": "VARCHAR",
        "semantic_signal_key": "VARCHAR",
    }

    raw_market_observation_columns = {
        "movement_phase": "VARCHAR",
        "phase_confidence_score": "FLOAT",
        "phase_reason": "VARCHAR",
        "is_late_entry_risk": "BOOLEAN DEFAULT FALSE",
        "is_profit_zone_candidate": "BOOLEAN DEFAULT FALSE",
        "distance_from_accumulation_zone_pct": "FLOAT",
        "distance_from_breakout_pct": "FLOAT",
        "operational_range_margin_pct": "FLOAT",
        "operational_range_quality": "VARCHAR",
        "alert_moment_type": "VARCHAR",
        "alert_reason": "VARCHAR",
    }

    signal_outcome_columns = {
        "price_after_24h": "FLOAT",
        "max_price_after_signal": "FLOAT",
        "min_price_after_signal": "FLOAT",
        "outcome_pct_24h": "FLOAT",
        "max_favorable_excursion_pct": "FLOAT",
        "max_adverse_excursion_pct": "FLOAT",
        "volume_after_signal": "FLOAT",
        "movement_continued": "BOOLEAN",
        "breakout_confirmed": "BOOLEAN",
        "late_signal_detected": "BOOLEAN",
        "outcome_label": "VARCHAR",
    }

    workspace_projection_columns = {
        "score_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "executability_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "movement_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "profile_version": "VARCHAR DEFAULT 'v1' NOT NULL",
        "reweighting_version": "VARCHAR DEFAULT 'v1' NOT NULL",
    }

    audit_columns = {
        "actor_user_id": "VARCHAR",
        "workspace_id": "VARCHAR",
    }

    user_columns = {
        "email": "VARCHAR",
        "organization_id": "VARCHAR",
        "must_change_password": "BOOLEAN DEFAULT FALSE NOT NULL",
        "created_by_user_id": "VARCHAR",
        "onboarding_completed_at": "DATETIME",
    }

    workspace_columns = {
        "organization_id": "VARCHAR",
    }

    default_org_payload = {
        "id": str(uuid.uuid4()),
        "name": "Default Organization",
        "slug": "default-org",
        "plan": "trial",
        "subscription_status": "trialing",
        "trial_ends_at": utcnow() + timedelta(days=14),
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }

    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
        for table_name in (
            "admin_users",
            "audit_logs",
            "organizations",
            "users",
            "workspaces",
            "workspace_memberships",
            "workspace_configs",
            "invites",
            "scanner_runtime_state",
            "scanner_cycle_audits",
            "signal_pipeline_events",
            "opportunity_snapshots",
            "technical_signals",
            "workspace_signal_projections",
            "raw_market_observations",
            "signal_outcomes",
            "signal_feedback",
            "repetition_counts",
        ):
            if table_name in existing_tables:
                continue
            await conn.run_sync(lambda sync_conn, name=table_name: Base.metadata.tables[name].create(sync_conn))

        for table_name, columns in (
            ("opportunities", opportunity_columns),
            ("scanner_runtime_state", scanner_runtime_columns),
            ("opportunity_snapshots", snapshot_columns),
            ("technical_signals", technical_signal_columns),
            ("workspace_signal_projections", workspace_projection_columns),
            ("raw_market_observations", raw_market_observation_columns),
            ("signal_outcomes", signal_outcome_columns),
        ):
            existing_columns = await conn.run_sync(
                lambda sync_conn, current_table=table_name: {
                    column["name"] for column in inspect(sync_conn).get_columns(current_table)
                }
            )
            for column_name, ddl in columns.items():
                if column_name in existing_columns:
                    continue
                await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

        audit_existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("audit_logs")}
        )
        for column_name, ddl in audit_columns.items():
            if column_name in audit_existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {column_name} {ddl}"))

        user_existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("users")}
        )
        for column_name, ddl in user_columns.items():
            if column_name in user_existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {ddl}"))

        workspace_existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("workspaces")}
        )
        for column_name, ddl in workspace_columns.items():
            if column_name in workspace_existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE workspaces ADD COLUMN {column_name} {ddl}"))

        organization_count = await conn.scalar(text("SELECT COUNT(1) FROM organizations"))
        if not organization_count:
            await conn.execute(
                text(
                    """
                    INSERT INTO organizations (
                        id,
                        name,
                        slug,
                        plan,
                        stripe_customer_id,
                        subscription_status,
                        trial_ends_at,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :name,
                        :slug,
                        :plan,
                        NULL,
                        :subscription_status,
                        :trial_ends_at,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                default_org_payload,
            )

        default_org_id = await conn.scalar(text("SELECT id FROM organizations ORDER BY created_at ASC LIMIT 1"))
        if default_org_id:
            if "organization_id" in user_columns:
                await conn.execute(
                    text("UPDATE users SET organization_id = :organization_id WHERE organization_id IS NULL"),
                    {"organization_id": default_org_id},
                )
            if "organization_id" in workspace_columns:
                await conn.execute(
                    text("UPDATE workspaces SET organization_id = :organization_id WHERE organization_id IS NULL"),
                    {"organization_id": default_org_id},
                )


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
