from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import Base, OpportunityRecord
from app.models.database import RawMarketObservationRecord, SignalOutcomeRecord, TechnicalSignalRecord, WorkspaceSignalProjectionRecord
from app.services import persistence
from app.models.schemas import AppConfig, Exchange, MovementRegime, MovementType, Opportunity


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


def test_workspace_operability_recalculates_slippage_from_profile():
    record = OpportunityRecord(
        id="profiled-history",
        exchange="binance",
        pair="BTC_BRL",
        score=70,
        volatility_pct=5,
        volume_24h=1000,
        quote_volume_24h=200000,
        liquidity_units=5000,
        spread_pct=0.2,
        movement_type="strong_range",
        last_price=100,
        change_pct=4,
        detected_at=datetime(2026, 4, 15, 18, 55, 30),
        duration_minutes=12,
        bid_notional_top_n=18000,
        ask_notional_top_n=17000,
        estimated_buy_slippage_bps=10,
        estimated_sell_slippage_bps=12,
        fillable_notional_within_slippage_cap=5000,
        baseline_order_notional_brl=1000,
        movement_persistence_score=0.5,
    )

    config = AppConfig(
        enabled_pairs=["BTC_BRL"],
        enabled_exchanges=[Exchange.BINANCE],
        trading_profile="agressivo",
        order_notional_brl=1500,
        max_entry_slippage_bps=35,
        max_exit_slippage_bps=45,
        min_quote_volume_brl=30000,
    )

    serialized = persistence.serialize_history_record(record, config)

    assert serialized["executability_score"] is not None
    assert serialized["operable_signal"] is True
    assert serialized["estimated_sell_slippage_bps"] > 12


def test_history_summary_returns_reduced_payload(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"history-summary-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)

        async with session_factory() as session:
            session.add(
                OpportunityRecord(
                    id="summary-1",
                    exchange="binance",
                    pair="BTC_BRL",
                    score=80,
                    technical_score=75,
                    executability_score=72,
                    trade_margin_score=44,
                    estimated_net_trade_edge_pct=0.88,
                    opportunity_type="trade",
                    volatility_pct=5,
                    volume_24h=1000,
                    quote_volume_24h=100000,
                    liquidity_units=5000,
                    spread_pct=0.2,
                    movement_type="strong_range",
                    last_price=100,
                    change_pct=4,
                    detected_at=datetime(2026, 4, 15, 18, 55, 30),
                    duration_minutes=10,
                )
            )
            await session.commit()

        rows = await persistence.get_history_summary(limit=10)

        assert rows == [
            {
                "id": "summary-1",
                "exchange": "binance",
                "pair": "BTC_BRL",
                "score": 80,
                "executability_score": 72,
                "trade_margin_score": 44,
                "estimated_net_trade_edge_pct": 0.88,
                "opportunity_type": "trade",
                "spread_pct": 0.2,
                "last_price": 100,
                "change_pct": 4,
                "movement_type": "strong_range",
                "movement_phase": "neutral",
                "is_late_entry_risk": False,
                "operational_range_margin_pct": None,
                "operational_range_quality": "none",
                "alert_moment_type": "neutral",
                "alert_reason": None,
                "alert_worthiness_score": None,
                "alert_trigger_type": None,
                "has_actionable_trigger": False,
                "alert_state_key": None,
                "alert_block_reason": None,
                "detected_at": "2026-04-15T18:55:30+00:00",
                "pipeline_status": "operational_opportunity",
                "visibility_reason": "trade_qualified",
                "operationally_visible": True,
            }
        ]
        assert "volume_24h" not in rows[0]
        assert "quote_volume_24h" not in rows[0]

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_history_summary_visibility_filters_operational_and_technical(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"history-visibility-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)

        detected_at = datetime(2026, 4, 15, 18, 55, 30, tzinfo=timezone.utc)
        async with session_factory() as session:
            session.add_all(
                [
                    OpportunityRecord(
                        id="operational-1",
                        exchange="binance",
                        pair="BTC_BRL",
                        score=82,
                        executability_score=70,
                        opportunity_type="trade",
                        volatility_pct=5,
                        volume_24h=1000,
                        quote_volume_24h=100000,
                        liquidity_units=5000,
                        spread_pct=0.2,
                        movement_type="strong_range",
                        last_price=100,
                        change_pct=4,
                        detected_at=detected_at,
                        duration_minutes=10,
                    ),
                    OpportunityRecord(
                        id="technical-1",
                        exchange="binance",
                        pair="DOGE_BRL",
                        score=30,
                        executability_score=20,
                        opportunity_type="avoid",
                        volatility_pct=8,
                        volume_24h=100,
                        quote_volume_24h=500,
                        liquidity_units=50,
                        spread_pct=4,
                        movement_type="weak",
                        last_price=1,
                        change_pct=8,
                        detected_at=detected_at - timedelta(minutes=1),
                        duration_minutes=10,
                    ),
                ]
            )
            await session.commit()

        all_rows = await persistence.get_history_summary(limit=10, visibility="all")
        operational_rows = await persistence.get_history_summary(limit=10, visibility="operational")
        technical_rows = await persistence.get_history_summary(limit=10, visibility="technical")

        assert [row["id"] for row in all_rows] == ["operational-1", "technical-1"]
        assert [row["id"] for row in operational_rows] == ["operational-1"]
        assert [row["id"] for row in technical_rows] == ["technical-1"]
        assert technical_rows[0]["pipeline_status"] == "blocked_signal"
        assert technical_rows[0]["visibility_reason"] == "opportunity_type_not_alertable"

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_filtered_analytics_includes_opportunity_type_and_margin_distribution(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"analytics-margin-{uuid.uuid4().hex}.db"

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
                        id="trade-1",
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
                        detected_at=now,
                        duration_minutes=10,
                        opportunity_type="trade",
                        estimated_net_trade_edge_pct=0.8,
                    ),
                    OpportunityRecord(
                        id="hold-1",
                        exchange="binance",
                        pair="ETH_BRL",
                        score=65,
                        volatility_pct=4,
                        volume_24h=900,
                        quote_volume_24h=90000,
                        liquidity_units=4000,
                        spread_pct=0.3,
                        movement_type="spike",
                        last_price=90,
                        change_pct=3,
                        detected_at=now,
                        duration_minutes=8,
                        opportunity_type="hold",
                        estimated_net_trade_edge_pct=0.4,
                    ),
                ]
            )
            await session.commit()

        analytics = await persistence.get_filtered_analytics(hours=1)

        assert analytics["opportunity_type_distribution"] == {
            "trade": 1,
            "hold": 1,
            "observe": 0,
            "avoid": 0,
        }
        assert analytics["avg_net_trade_edge_by_type"] == {
            "trade": 0.8,
            "hold": 0.4,
        }

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_save_opportunities_uses_semantic_dedup(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"semantic-dedup-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)

        base_kwargs = dict(
            exchange=Exchange.BINANCE,
            pair="BTC_BRL",
            score=70,
            volatility_pct=5,
            volume_24h=1000,
            quote_volume_24h=200000,
            liquidity_units=5000,
            spread_pct=0.2,
            movement_type=MovementType.STRONG_RANGE,
            movement_regime=MovementRegime.TREND_CONTINUATION,
            last_price=100,
            change_pct=4,
            duration_minutes=5,
        )

        opp1 = Opportunity(id="sem-1", semantic_signal_key="binance:BTC_BRL:strong_range:trend", **base_kwargs)
        opp2 = Opportunity(id="sem-2", semantic_signal_key="binance:BTC_BRL:strong_range:trend", **base_kwargs)

        await persistence.save_opportunities([opp1])
        await persistence.save_opportunities([opp2])

        rows = await persistence.get_history(limit=10)
        assert [row["id"] for row in rows] == ["sem-1"]

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_history_retention_prunes_all_historical_layers(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"retention-layers-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)

        now = datetime.now(timezone.utc)
        stale = now - timedelta(days=120)
        recent = now - timedelta(days=2)

        async with session_factory() as session:
            session.add_all(
                [
                    TechnicalSignalRecord(
                        id="stale-signal",
                        exchange="binance",
                        pair="BTC_BRL",
                        technical_score=70,
                        volatility_pct=5,
                        volume_24h=1000,
                        quote_volume_24h=100000,
                        liquidity_units=5000,
                        spread_pct=0.2,
                        movement_type="strong_range",
                        last_price=100,
                        change_pct=4,
                        detected_at=stale,
                    ),
                    TechnicalSignalRecord(
                        id="recent-signal",
                        exchange="binance",
                        pair="ETH_BRL",
                        technical_score=60,
                        volatility_pct=4,
                        volume_24h=800,
                        quote_volume_24h=90000,
                        liquidity_units=4000,
                        spread_pct=0.3,
                        movement_type="spike",
                        last_price=90,
                        change_pct=3,
                        detected_at=recent,
                    ),
                    WorkspaceSignalProjectionRecord(
                        id="stale-projection",
                        workspace_id="workspace-1",
                        technical_signal_id="stale-signal",
                        workspace_score=70,
                        created_at=stale,
                    ),
                    RawMarketObservationRecord(
                        id="stale-raw",
                        observation_cycle_id="cycle-old",
                        exchange="binance",
                        pair="BTC_BRL",
                        movement_type="strong_range",
                        last_price=100,
                        quote_volume_24h=100000,
                        liquidity_units=5000,
                        spread_pct=0.2,
                        detected_at=stale,
                        created_at=stale,
                    ),
                    SignalOutcomeRecord(
                        id="stale-outcome",
                        technical_signal_id="stale-signal",
                        exchange="binance",
                        pair="BTC_BRL",
                        entry_price=100,
                        signal_detected_at=stale,
                        created_at=stale,
                    ),
                ]
            )
            await session.commit()

        removed = await persistence.purge_history_older_than(retention_days=90, now=now)

        async with session_factory() as session:
            stale_signal = await session.get(TechnicalSignalRecord, "stale-signal")
            recent_signal = await session.get(TechnicalSignalRecord, "recent-signal")
            stale_projection = await session.get(WorkspaceSignalProjectionRecord, "stale-projection")
            stale_raw = await session.get(RawMarketObservationRecord, "stale-raw")
            stale_outcome = await session.get(SignalOutcomeRecord, "stale-outcome")

        assert removed == 0
        assert stale_signal is None
        assert recent_signal is not None
        assert stale_projection is None
        assert stale_raw is None
        assert stale_outcome is None

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
