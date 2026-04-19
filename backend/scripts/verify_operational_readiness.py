from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.models.database import (  # noqa: E402
    OpportunityRecord,
    RawMarketObservationRecord,
    SignalOutcomeRecord,
    TechnicalSignalRecord,
    WorkspaceSignalProjectionRecord,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def scalar(session_factory, query) -> int:
    async with session_factory() as session:
        return int((await session.scalar(query)) or 0)


async def main() -> None:
    recent_cutoff = utcnow() - timedelta(hours=24)
    connect_args = {"statement_cache_size": 0}
    if settings.database_url.startswith("sqlite+aiosqlite://"):
        connect_args = {}
    engine = create_async_engine(settings.database_url, echo=False, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with engine.connect() as conn:
            existing_tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
            column_map = await conn.run_sync(
                lambda sync_conn: {
                    table_name: {column["name"] for column in inspect(sync_conn).get_columns(table_name)}
                    for table_name in inspect(sync_conn).get_table_names()
                }
            )

        def table_present(name: str) -> bool:
            return name in existing_tables

        def column_present(table_name: str, column_name: str) -> bool:
            return column_name in column_map.get(table_name, set())

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema": {
                "raw_market_observations_present": table_present("raw_market_observations"),
                "signal_outcomes_present": table_present("signal_outcomes"),
                "technical_signals_present": table_present("technical_signals"),
                "workspace_signal_projections_present": table_present("workspace_signal_projections"),
                "opportunities_movement_regime_present": column_present("opportunities", "movement_regime"),
                "opportunities_semantic_signal_key_present": column_present("opportunities", "semantic_signal_key"),
                "opportunities_baseline_order_notional_present": column_present("opportunities", "baseline_order_notional_brl"),
                "opportunities_reweighting_version_present": column_present("opportunities", "reweighting_version"),
            },
            "counts": {
                "opportunities_total": await scalar(session_factory, select(func.count()).select_from(OpportunityRecord)),
                "raw_market_observations_total": (
                    await scalar(session_factory, select(func.count()).select_from(RawMarketObservationRecord))
                    if table_present("raw_market_observations")
                    else None
                ),
                "technical_signals_total": (
                    await scalar(session_factory, select(func.count()).select_from(TechnicalSignalRecord))
                    if table_present("technical_signals")
                    else None
                ),
                "workspace_signal_projections_total": (
                    await scalar(session_factory, select(func.count()).select_from(WorkspaceSignalProjectionRecord))
                    if table_present("workspace_signal_projections")
                    else None
                ),
                "signal_outcomes_total": (
                    await scalar(session_factory, select(func.count()).select_from(SignalOutcomeRecord))
                    if table_present("signal_outcomes")
                    else None
                ),
            },
            "recent_24h": {
                "raw_market_observations": (
                    await scalar(
                        session_factory,
                        select(func.count())
                        .select_from(RawMarketObservationRecord)
                        .where(RawMarketObservationRecord.detected_at >= recent_cutoff),
                    )
                    if table_present("raw_market_observations")
                    else None
                ),
                "technical_signals": (
                    await scalar(
                        session_factory,
                        select(func.count())
                        .select_from(TechnicalSignalRecord)
                        .where(TechnicalSignalRecord.detected_at >= recent_cutoff),
                    )
                    if table_present("technical_signals")
                    else None
                ),
                "signal_outcomes": (
                    await scalar(
                        session_factory,
                        select(func.count())
                        .select_from(SignalOutcomeRecord)
                        .where(SignalOutcomeRecord.signal_detected_at >= recent_cutoff),
                    )
                    if table_present("signal_outcomes")
                    else None
                ),
            },
            "coverage": {
                "movement_regime_populated": await scalar(
                    session_factory,
                    select(func.count())
                    .select_from(OpportunityRecord)
                    .where(OpportunityRecord.movement_regime.is_not(None)),
                ) if column_present("opportunities", "movement_regime") else None,
                "semantic_signal_key_populated": await scalar(
                    session_factory,
                    select(func.count())
                    .select_from(OpportunityRecord)
                    .where(OpportunityRecord.semantic_signal_key.is_not(None)),
                ) if column_present("opportunities", "semantic_signal_key") else None,
                "baseline_order_notional_populated": await scalar(
                    session_factory,
                    select(func.count())
                    .select_from(OpportunityRecord)
                    .where(OpportunityRecord.baseline_order_notional_brl.is_not(None)),
                ) if column_present("opportunities", "baseline_order_notional_brl") else None,
                "movement_persistence_populated": await scalar(
                    session_factory,
                    select(func.count())
                    .select_from(OpportunityRecord)
                    .where(OpportunityRecord.movement_persistence_score.is_not(None)),
                ) if column_present("opportunities", "movement_persistence_score") else None,
                "reweighting_version_populated": await scalar(
                    session_factory,
                    select(func.count())
                    .select_from(OpportunityRecord)
                    .where(OpportunityRecord.reweighting_version.is_not(None)),
                ) if column_present("opportunities", "reweighting_version") else None,
            },
        }

        print(json.dumps(summary, indent=2, ensure_ascii=True))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
