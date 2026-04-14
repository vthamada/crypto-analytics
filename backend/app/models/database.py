from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, Text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.models.schemas import Exchange, MovementType


class Base(DeclarativeBase):
    pass


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
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    duration_minutes = Column(Float, default=0.0)


class ConfigRecord(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Engine setup
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
