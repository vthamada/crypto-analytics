from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import Base, OpportunityRecord
from app.services import persistence


def test_filtered_analytics_respects_hours(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"analytics-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)

        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            session.add_all(
                [
                    OpportunityRecord(
                        id="recent-1",
                        exchange="binance",
                        pair="BTC_BRL",
                        score=80,
                        volatility_pct=5,
                        volume_24h=1000,
                        quote_volume_24h=100000,
                        liquidity_units=5000,
                        spread_pct=0.2,
                        movement_type="strong_range",
                        last_price=100,
                        change_pct=4,
                        detected_at=now - timedelta(minutes=30),
                        duration_minutes=10,
                    ),
                    OpportunityRecord(
                        id="old-1",
                        exchange="binance",
                        pair="ETH_BRL",
                        score=50,
                        volatility_pct=3,
                        volume_24h=500,
                        quote_volume_24h=30000,
                        liquidity_units=1500,
                        spread_pct=0.4,
                        movement_type="weak",
                        last_price=80,
                        change_pct=1,
                        detected_at=now - timedelta(hours=48),
                        duration_minutes=15,
                    ),
                ]
            )
            await session.commit()

        analytics = await persistence.get_filtered_analytics(hours=1)

        assert analytics["total_records"] == 1
        assert analytics["top_pairs"] == [{"pair": "BTC_BRL", "count": 1}]
        assert analytics["score_distribution"]["80-100"] == 1

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
