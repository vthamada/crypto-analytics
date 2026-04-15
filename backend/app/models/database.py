from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    return datetime.now(timezone.utc)


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


class UserRecord(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="member", index=True)
    token_version = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    password_updated_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
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


# Engine setup
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_sync_database_url() -> str:
    return (
        settings.database_url
        .replace("sqlite+aiosqlite://", "sqlite://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )


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
    expected_columns = {
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
    }

    audit_columns = {
        "actor_user_id": "VARCHAR",
        "workspace_id": "VARCHAR",
    }

    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
        for table_name in (
            "admin_users",
            "audit_logs",
            "users",
            "workspaces",
            "workspace_memberships",
            "workspace_configs",
        ):
            if table_name in existing_tables:
                continue
            await conn.run_sync(lambda sync_conn, name=table_name: Base.metadata.tables[name].create(sync_conn))

        existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("opportunities")}
        )
        for column_name, ddl in expected_columns.items():
            if column_name in existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE opportunities ADD COLUMN {column_name} {ddl}"))

        audit_existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("audit_logs")}
        )
        for column_name, ddl in audit_columns.items():
            if column_name in audit_existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {column_name} {ddl}"))


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
