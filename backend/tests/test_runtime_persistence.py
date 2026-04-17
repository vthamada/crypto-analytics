from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import (
    Base,
    OpportunityRecord,
    OpportunitySnapshotRecord,
    TechnicalSignalRecord,
)
from app.models.schemas import Exchange, MovementType, Opportunity
from app.services import persistence, shared_state


def test_runtime_persistence_normalizes_aware_detected_at(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"runtime-persistence-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(persistence, "async_session", session_factory)
        monkeypatch.setattr(shared_state, "async_session", session_factory)

        opportunity = Opportunity(
            id="opp-runtime-1",
            exchange=Exchange.BINANCE,
            pair="BTC_BRL",
            score=74.2,
            technical_score=70.1,
            score_version="v1",
            volatility_pct=3.4,
            volume_24h=1500.0,
            quote_volume_24h=300000.0,
            liquidity_units=4200.0,
            spread_pct=0.22,
            movement_type=MovementType.SPIKE,
            last_price=350000.0,
            change_pct=2.6,
            detected_at=datetime.now(timezone.utc),
            historical_confidence=1.0,
            volatility_score=0.41,
            volume_score=0.52,
            liquidity_score=0.83,
            spread_score=0.78,
            repetition_score=0.35,
            movement_multiplier=1.15,
        )

        await persistence.save_opportunities([opportunity])
        signal_map = await shared_state.save_technical_signals([opportunity])
        opportunity.technical_signal_id = signal_map[opportunity.id]
        await shared_state.write_opportunity_snapshots([opportunity], "cycle-test")
        await shared_state.create_pending_outcomes(
            [
                {
                    "technical_signal_id": opportunity.technical_signal_id,
                    "exchange": opportunity.exchange.value,
                    "pair": opportunity.pair,
                    "entry_price": opportunity.last_price,
                    "signal_detected_at": opportunity.detected_at,
                }
            ]
        )

        async with session_factory() as session:
            history_row = await session.get(OpportunityRecord, opportunity.id)
            snapshot_row = await session.get(OpportunitySnapshotRecord, opportunity.id)
            signal_row = await session.get(TechnicalSignalRecord, opportunity.technical_signal_id)

        assert history_row is not None
        assert snapshot_row is not None
        assert signal_row is not None
        assert history_row.detected_at.tzinfo is None
        assert snapshot_row.detected_at.tzinfo is None
        assert signal_row.detected_at.tzinfo is None

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_runtime_writers_strip_timezone_before_persisting(monkeypatch):
    opportunity = Opportunity(
        id="opp-runtime-aware",
        exchange=Exchange.BINANCE,
        pair="ETH_BRL",
        score=66.4,
        technical_score=61.0,
        score_version="v1",
        volatility_pct=2.9,
        volume_24h=900.0,
        quote_volume_24h=180000.0,
        liquidity_units=3000.0,
        spread_pct=0.31,
        movement_type=MovementType.WEAK,
        last_price=18000.0,
        change_pct=1.4,
        detected_at=datetime.now(timezone.utc),
        historical_confidence=1.0,
        volatility_score=0.31,
        volume_score=0.44,
        liquidity_score=0.73,
        spread_score=0.69,
        repetition_score=0.18,
        movement_multiplier=0.7,
        technical_signal_id="signal-aware",
    )

    class _Result:
        def all(self):
            return []

    class _Session:
        def __init__(self):
            self.added = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def add(self, record):
            self.added.append(record)

        async def execute(self, query):
            return _Result()

        async def commit(self):
            return None

    history_session = _Session()
    signal_session = _Session()
    snapshot_session = _Session()
    outcome_session = _Session()

    async def _run():
        monkeypatch.setattr(persistence, "async_session", lambda: history_session)
        monkeypatch.setattr(shared_state, "async_session", lambda: signal_session)
        await persistence.save_opportunities([opportunity])
        await shared_state.save_technical_signals([opportunity])

        monkeypatch.setattr(shared_state, "async_session", lambda: snapshot_session)
        await shared_state.write_opportunity_snapshots([opportunity], "cycle-aware")

        monkeypatch.setattr(shared_state, "async_session", lambda: outcome_session)
        await shared_state.create_pending_outcomes(
            [
                {
                    "technical_signal_id": opportunity.technical_signal_id,
                    "exchange": opportunity.exchange.value,
                    "pair": opportunity.pair,
                    "entry_price": opportunity.last_price,
                    "signal_detected_at": opportunity.detected_at,
                }
            ]
        )

    asyncio.run(_run())

    assert history_session.added[0].detected_at.tzinfo is None
    assert signal_session.added[0].detected_at.tzinfo is None
    assert snapshot_session.added[0].detected_at.tzinfo is None
    assert outcome_session.added[0].signal_detected_at.tzinfo is None
