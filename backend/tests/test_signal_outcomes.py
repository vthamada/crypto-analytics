from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import Base, SignalOutcomeRecord
from app.services import shared_state


def test_signal_outcomes_preserve_first_window_and_finish_at_4h(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"signal-outcomes-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)

        detected_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await shared_state.create_pending_outcomes(
            [
                {
                    "technical_signal_id": "sig-1",
                    "exchange": "binance",
                    "pair": "BTC_BRL",
                    "entry_price": 100.0,
                    "signal_detected_at": detected_at,
                }
            ]
        )

        async with session_factory() as session:
            outcome = (await session.execute(select(SignalOutcomeRecord))).scalar_one()
            outcome_id = outcome.id

        await shared_state.update_outcome(
            outcome_id,
            price_after_5m=101.0,
            max_price_1h=103.0,
            min_price_1h=99.0,
        )
        await shared_state.update_outcome(
            outcome_id,
            price_after_5m=105.0,
            price_after_15m=102.0,
            price_after_1h=104.0,
            max_price_1h=106.0,
            min_price_1h=98.0,
        )

        async with session_factory() as session:
            row = await session.get(SignalOutcomeRecord, outcome_id)
            assert row is not None
            assert row.price_after_5m == 101.0
            assert row.price_after_15m == 102.0
            assert row.price_after_1h == 104.0
            assert row.max_price_1h == 106.0
            assert row.min_price_1h == 98.0
            assert row.evaluated_at is None

        pending = await shared_state.get_pending_outcomes(min_age_minutes=5, max_age_hours=5, limit=10)
        assert [item["id"] for item in pending] == [outcome_id]

        await shared_state.update_outcome(outcome_id, price_after_4h=108.0)

        async with session_factory() as session:
            row = await session.get(SignalOutcomeRecord, outcome_id)
            assert row is not None
            assert row.price_after_4h == 108.0
            assert row.evaluated_at is not None

        pending = await shared_state.get_pending_outcomes(min_age_minutes=5, max_age_hours=5, limit=10)
        assert pending == []

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
