from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.database import (
    Base,
    OpportunityRecord,
    OpportunitySnapshotRecord,
    ScannerCycleAuditRecord,
    ScannerPairStateRecord,
    ScannerRuntimeStateRecord,
    SignalPipelineEventRecord,
    TechnicalSignalRecord,
    WorkspaceSignalProjectionRecord,
)
from app.models.schemas import Exchange, MovementType, Opportunity
from app.services import persistence, shared_state


def test_pipeline_audit_compact_mode_filters_common_discards(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"pipeline-compact-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        monkeypatch.setattr(shared_state.settings, "pipeline_audit_enabled", True)
        monkeypatch.setattr(shared_state.settings, "pipeline_audit_mode", "compact")

        created_at = datetime.now(timezone.utc)
        saved = await shared_state.save_signal_pipeline_events(
            "cycle-compact",
            [
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "QUIET_BRL",
                    "stage": "light_scan",
                    "status": "discarded",
                    "reason": "volume_below_minimum",
                    "created_at": created_at,
                },
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "light_scan",
                    "status": "candidate",
                    "reason": "candidate",
                    "created_at": created_at,
                },
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "WBTC_BRL",
                    "stage": "deep_scan",
                    "status": "near_miss",
                    "reason": "insufficient_volume",
                    "event_type": "near_miss",
                    "created_at": created_at,
                },
            ],
        )

        async with session_factory() as session:
            rows = (await session.execute(SignalPipelineEventRecord.__table__.select())).fetchall()

        assert saved == 2
        assert [row.pair for row in rows] == ["SOL_BRL", "WBTC_BRL"]

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_pipeline_audit_can_be_disabled(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"pipeline-disabled-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        monkeypatch.setattr(shared_state.settings, "pipeline_audit_enabled", False)

        saved = await shared_state.save_signal_pipeline_events(
            "cycle-disabled",
            [
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "light_scan",
                    "status": "candidate",
                    "reason": "candidate",
                    "created_at": datetime.now(timezone.utc),
                }
            ],
        )

        async with session_factory() as session:
            rows = (await session.execute(SignalPipelineEventRecord.__table__.select())).fetchall()

        assert saved == 0
        assert rows == []

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_audit_retention_uses_configured_windows(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"audit-retention-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        monkeypatch.setattr(shared_state.settings, "pipeline_event_retention_days", 1)
        monkeypatch.setattr(shared_state.settings, "scanner_cycle_audit_retention_days", 2)

        now = datetime.now(timezone.utc)
        async with session_factory() as session:
            session.add_all(
                [
                    SignalPipelineEventRecord(
                        cycle_id="old-event",
                        exchange="novadax",
                        pair="SOL_BRL",
                        stage="light_scan",
                        status="candidate",
                        created_at=now - timedelta(days=2),
                    ),
                    SignalPipelineEventRecord(
                        cycle_id="new-event",
                        exchange="novadax",
                        pair="WBTC_BRL",
                        stage="light_scan",
                        status="candidate",
                        created_at=now,
                    ),
                    ScannerCycleAuditRecord(
                        cycle_id="old-cycle",
                        status="completed",
                        started_at=now - timedelta(days=3),
                        created_at=now - timedelta(days=3),
                    ),
                    ScannerCycleAuditRecord(
                        cycle_id="new-cycle",
                        status="completed",
                        started_at=now,
                        created_at=now,
                    ),
                ]
            )
            await session.commit()

        await shared_state.run_audit_retention_if_due(now=now)

        async with session_factory() as session:
            event_rows = (await session.execute(SignalPipelineEventRecord.__table__.select())).fetchall()
            cycle_rows = (await session.execute(ScannerCycleAuditRecord.__table__.select())).fetchall()

        assert [row.cycle_id for row in event_rows] == ["new-event"]
        assert [row.cycle_id for row in cycle_rows] == ["new-cycle"]

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


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
            executability_version="v1",
            movement_version="v1",
            profile_version="v1",
            technical_signal_id=None,
            executability_score=61.4,
            executability_band="fair",
            interesting_signal=True,
            operable_signal=False,
            volatility_pct=3.4,
            volume_24h=1500.0,
            quote_volume_24h=300000.0,
            liquidity_units=4200.0,
            bid_notional_top_n=22000.0,
            ask_notional_top_n=21000.0,
            total_notional_top_n=43000.0,
            spread_pct=0.22,
            estimated_buy_slippage_bps=12.5,
            estimated_sell_slippage_bps=16.8,
            fillable_notional_within_slippage_cap=5000.0,
            movement_type=MovementType.SPIKE,
            movement_persistence_score=0.37,
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
        await shared_state.save_workspace_projections(
            workspace_id="workspace-1",
            technical_signal_id=opportunity.technical_signal_id,
            workspace_score=opportunity.score,
        )
        await shared_state.update_scanner_runtime_state(
            opportunities_count=1,
            scan_diagnostics={"total_pairs": 3, "deep_candidates": 1, "opportunities": 1},
        )
        runtime_state = await shared_state.get_scanner_runtime_state()
        assert runtime_state is not None
        assert runtime_state["last_scan_diagnostics"]["total_pairs"] == 3
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
            projection_result = await session.execute(
                WorkspaceSignalProjectionRecord.__table__.select().limit(1)
            )
            projection_row = projection_result.first()
            runtime_row = await session.get(ScannerRuntimeStateRecord, "singleton")

        assert history_row is not None
        assert snapshot_row is not None
        assert signal_row is not None
        assert projection_row is not None
        assert runtime_row is not None
        assert history_row.detected_at.tzinfo is None
        assert snapshot_row.detected_at.tzinfo is None
        assert signal_row.detected_at.tzinfo is None
        assert history_row.executability_version == "v1"
        assert history_row.movement_version == "v1"
        assert history_row.profile_version == "v1"
        assert history_row.executability_score == 61.4
        assert history_row.operational_score == opportunity.score
        assert snapshot_row.executability_version == "v1"
        assert snapshot_row.operational_score == opportunity.score
        assert snapshot_row.bid_notional_top_n == 22000.0
        assert signal_row.executability_version == "v1"
        assert runtime_row.executability_version == "v1"
        assert runtime_row.movement_version == "v1"
        assert runtime_row.profile_version == "v1"
        assert projection_row.score_version == "v1"
        assert projection_row.executability_version == "v1"

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_scanner_pair_state_persistence(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"scanner-pair-state-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)

        now = datetime.now(timezone.utc)
        saved = await shared_state.save_scanner_pair_states(
            {
                "novadax:XRP_BRL": {
                    "exchange": "novadax",
                    "pair": "XRP_BRL",
                    "temperature": "cold",
                    "last_light_scan_at": now,
                    "last_deep_scan_at": None,
                    "failure_count": 2,
                    "cooldown_until": now,
                    "last_discard_reason": "ticker_failed",
                }
            }
        )
        loaded = await shared_state.load_scanner_pair_states()

        async with session_factory() as session:
            row = await session.get(ScannerPairStateRecord, "novadax:XRP_BRL")

        assert saved == 1
        assert row is not None
        assert row.cooldown_until.tzinfo is None
        assert loaded["novadax:XRP_BRL"]["temperature"] == "cold"
        assert loaded["novadax:XRP_BRL"]["failure_count"] == 2
        assert loaded["novadax:XRP_BRL"]["last_discard_reason"] == "ticker_failed"

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_funnel_quality_metrics_summarize_cycles_and_alert_blocks(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"funnel-quality-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        started_at = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        await shared_state.save_signal_pipeline_events(
            "cycle-quality",
            [
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "light_scan",
                    "status": "candidate",
                    "reason": "candidate",
                    "created_at": started_at,
                },
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "alert",
                    "status": "blocked",
                    "reason": "no_state_change",
                    "workspace_id": "workspace-1",
                    "created_at": started_at,
                },
            ],
        )
        await shared_state.save_scanner_cycle_audit(
            cycle_id="cycle-quality",
            started_at=started_at,
            completed_at=started_at,
            duration_ms=250.0,
            diagnostics={
                "total_pairs": 20,
                "brl_pairs": 20,
                "light_candidates": 4,
                "deep_candidates": 2,
                "deep_completed": 2,
                "light_discard_reasons": {"volume_below_minimum": 5},
            },
            signals_created=2,
            shortlist_count=1,
            alerts_created=1,
            alerts_sent=0,
            block_reasons={"no_state_change": 1},
        )

        metrics = await shared_state.get_funnel_quality_metrics(
            from_time=started_at,
            to_time=started_at,
            workspace_id="workspace-1",
            exchange="novadax",
            pair="SOL_BRL",
        )

        assert metrics["cycle_totals"]["cycles"] == 1
        assert metrics["cycle_totals"]["total_pairs"] == 20
        assert metrics["rates"]["light_candidate_rate"] == 0.2
        assert metrics["rates"]["alert_send_rate"] == 0.0
        assert metrics["top_discard_reasons"] == [{"reason": "volume_below_minimum", "count": 5}]
        assert metrics["top_alert_block_reasons"] == [{"reason": "no_state_change", "count": 1}]
        assert metrics["stage_distribution"]["alert"] == 1

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())


def test_get_near_misses_returns_compact_audit_events(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"near-misses-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        created_at = datetime.now(timezone.utc)
        await shared_state.save_signal_pipeline_events(
            "cycle-near-miss",
            [
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "promotion",
                    "status": "near_miss",
                    "reason": "candidate_limit_lower_priority",
                    "event_type": "near_miss",
                    "details": {
                        "preliminary_score": 58.0,
                        "distance_to_selected_score": 3.0,
                        "failed_metric": "preliminary_score",
                    },
                    "created_at": created_at,
                },
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "BTC_BRL",
                    "stage": "ranking",
                    "status": "ranked",
                    "reason": "entered_cycle_ranking",
                    "details": {"score": 80.0},
                    "created_at": created_at,
                },
            ],
        )

        near_misses = await shared_state.get_near_misses(
            exchange="novadax",
            pair="SOL_BRL",
            from_time=created_at.replace(tzinfo=timezone.utc),
            to_time=created_at.replace(tzinfo=timezone.utc),
        )

        assert len(near_misses) == 1
        assert near_misses[0]["pair"] == "SOL_BRL"
        assert near_misses[0]["reason"] == "candidate_limit_lower_priority"
        assert near_misses[0]["details"]["failed_metric"] == "preliminary_score"

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
        executability_version="v1",
        movement_version="v1",
        profile_version="v1",
        volatility_pct=2.9,
        volume_24h=900.0,
        quote_volume_24h=180000.0,
        liquidity_units=3000.0,
        bid_notional_top_n=8000.0,
        ask_notional_top_n=7600.0,
        total_notional_top_n=15600.0,
        spread_pct=0.31,
        estimated_buy_slippage_bps=22.0,
        estimated_sell_slippage_bps=28.0,
        fillable_notional_within_slippage_cap=2000.0,
        movement_type=MovementType.WEAK,
        movement_persistence_score=0.18,
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
        executability_score=42.2,
        executability_band="poor",
        interesting_signal=True,
        operable_signal=False,
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
    assert history_session.added[0].executability_version == "v1"
    assert snapshot_session.added[0].executability_version == "v1"
    assert signal_session.added[0].executability_version == "v1"


def test_pipeline_audit_persists_cycle_and_missed_signal_timeline(monkeypatch):
    db_dir = Path(__file__).resolve().parent / ".tmp"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"pipeline-audit-{uuid.uuid4().hex}.db"

    async def run_test():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        monkeypatch.setattr(shared_state, "async_session", session_factory)
        started_at = datetime.now(timezone.utc)
        await shared_state.save_signal_pipeline_events(
            "cycle-audit",
            [
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "light_scan",
                    "status": "candidate",
                    "reason": "candidate",
                    "details": {"preliminary_score": 81.2},
                    "created_at": started_at,
                },
                {
                    "exchange": Exchange.NOVADAX,
                    "pair": "SOL_BRL",
                    "stage": "alert",
                    "status": "blocked",
                    "reason": "below_alert_threshold",
                    "details": {"score": 58.0},
                    "created_at": started_at,
                },
            ],
        )
        sent_count = await shared_state.count_workspace_alerts_sent_since("workspace-1", started_at.replace(tzinfo=timezone.utc))
        assert sent_count == 0
        await shared_state.save_scanner_cycle_audit(
            cycle_id="cycle-audit",
            started_at=started_at,
            completed_at=started_at,
            duration_ms=123.0,
            diagnostics={
                "total_pairs": 10,
                "brl_pairs": 10,
                "light_candidates": 2,
                "deep_candidates": 1,
                "deep_completed": 1,
                "light_discard_reasons": {"volume_below_minimum": 3},
            },
            signals_created=1,
            shortlist_count=1,
            alerts_created=1,
            alerts_sent=0,
            block_reasons={"below_alert_threshold": 1},
        )

        diagnostic = await shared_state.get_missed_signal_diagnostic(
            exchange="novadax",
            pair="SOL_BRL",
            from_time=started_at.replace(tzinfo=timezone.utc),
            to_time=started_at.replace(tzinfo=timezone.utc),
        )

        async with session_factory() as session:
            event_result = await session.execute(SignalPipelineEventRecord.__table__.select())
            cycle_result = await session.execute(ScannerCycleAuditRecord.__table__.select())

        assert len(event_result.fetchall()) == 2
        assert len(cycle_result.fetchall()) == 1
        assert diagnostic["status"] == "events_found"
        assert diagnostic["final_state"] == "discarded_before_alert"
        assert diagnostic["root_cause_stage"] == "alert"
        assert diagnostic["root_cause_reason"] == "below_alert_threshold"
        assert [event["stage"] for event in diagnostic["timeline"]] == ["light_scan", "alert"]
        assert diagnostic["cycle_summaries"][0]["alerts_sent"] == 0
        assert diagnostic["cycle_summaries"][0]["block_reasons"] == {"below_alert_threshold": 1}

        await engine.dispose()
        if db_path.exists():
            db_path.unlink()

    asyncio.run(run_test())
