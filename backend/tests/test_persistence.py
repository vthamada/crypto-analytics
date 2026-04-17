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


def test_history_retention_prunes_only_expired_records(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"retention-{uuid.uuid4().hex}.db"

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
                        id="recent-kept",
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
                        detected_at=now - timedelta(days=20),
                        duration_minutes=10,
                    ),
                    OpportunityRecord(
                        id="stale-removed",
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
                        detected_at=now - timedelta(days=120),
                        duration_minutes=15,
                    ),
                ]
            )
            await session.commit()

        removed = await persistence.purge_history_older_than(retention_days=90, now=now)
        remaining_rows = await persistence.get_history(limit=10)

        assert removed == 1
        assert [row["id"] for row in remaining_rows] == ["recent-kept"]

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_history_retention_honors_check_interval(monkeypatch):
    async def run_test():
        reference_time = datetime.now(timezone.utc)
        calls: list[tuple[int, datetime]] = []

        async def fake_purge(*, retention_days: int, now: datetime | None = None):
            calls.append((retention_days, now or reference_time))
            return 2

        monkeypatch.setattr(persistence, "_last_history_retention_run", None)
        monkeypatch.setattr(persistence, "purge_history_older_than", fake_purge)
        monkeypatch.setattr(persistence.settings, "history_retention_days", 90)
        monkeypatch.setattr(persistence.settings, "history_retention_check_minutes", 60)

        first = await persistence.run_history_retention_if_due(now=reference_time)
        second = await persistence.run_history_retention_if_due(now=reference_time + timedelta(minutes=10))
        third = await persistence.run_history_retention_if_due(now=reference_time + timedelta(minutes=61))

        assert first == 2
        assert second == 0
        assert third == 2
        assert len(calls) == 2

    asyncio.run(run_test())


def test_serialize_history_record_marks_naive_detected_at_as_utc():
    record = OpportunityRecord(
        id="naive-datetime",
        exchange="binance",
        pair="BTC_BRL",
        score=80,
        technical_score=75,
        score_version="v1",
        executability_version="v1",
        movement_version="v1",
        profile_version="v1",
        technical_signal_id="sig-history-1",
        executability_score=62.5,
        executability_band="fair",
        interesting_signal=True,
        operable_signal=False,
        volatility_pct=5,
        volume_24h=1000,
        quote_volume_24h=100000,
        liquidity_units=5000,
        bid_notional_top_n=12000,
        ask_notional_top_n=11000,
        total_notional_top_n=23000,
        spread_pct=0.2,
        estimated_buy_slippage_bps=14.0,
        estimated_sell_slippage_bps=19.0,
        fillable_notional_within_slippage_cap=5000,
        movement_type="strong_range",
        movement_persistence_score=0.45,
        last_price=100,
        change_pct=4,
        detected_at=datetime(2026, 4, 15, 18, 55, 30),
        duration_minutes=10,
    )

    serialized = persistence.serialize_history_record(record)

    assert serialized["detected_at"] == "2026-04-15T18:55:30+00:00"
    assert serialized["technical_score"] == 75
    assert serialized["score_version"] == "v1"
    assert serialized["executability_version"] == "v1"
    assert serialized["movement_version"] == "v1"
    assert serialized["profile_version"] == "v1"
    assert serialized["technical_signal_id"] == "sig-history-1"
    assert serialized["executability_score"] == 62.5
    assert serialized["executability_band"] == "fair"
    assert serialized["interesting_signal"] is True
    assert serialized["operable_signal"] is False
    assert serialized["bid_notional_top_n"] == 12000
    assert serialized["ask_notional_top_n"] == 11000
    assert serialized["total_notional_top_n"] == 23000
    assert serialized["estimated_buy_slippage_bps"] == 14.0
    assert serialized["estimated_sell_slippage_bps"] == 19.0
    assert serialized["fillable_notional_within_slippage_cap"] == 5000
    assert serialized["movement_persistence_score"] == 0.45
