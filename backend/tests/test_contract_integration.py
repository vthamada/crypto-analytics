"""Contract integration tests for P2.

These tests freeze the observable API contracts so that scanner decoupling,
technical scoring, and shared state changes do not cause silent regressions.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.models.schemas import (
    AppConfig,
    Exchange,
    MovementType,
    Opportunity,
)
from app.services.auth import UserSession


def _create_client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def _make_workspace(*, role: str = "owner", **overrides):
    payload = {
        "id": "ws-contract",
        "slug": "contract",
        "name": "Contract",
        "role": role,
        "is_active": True,
    }
    payload.update(overrides)
    return type("W", (), payload)()


def _fake_opportunity(**overrides) -> Opportunity:
    defaults = dict(
        id="opp-1",
        exchange=Exchange.BINANCE,
        pair="BTC_BRL",
        score=72.5,
        technical_score=68.3,
        score_version="v1",
        executability_version="v1",
        movement_version="v1",
        profile_version="v1",
        executability_score=None,
        executability_band=None,
        interesting_signal=None,
        operable_signal=None,
        bid_notional_top_n=None,
        ask_notional_top_n=None,
        total_notional_top_n=None,
        estimated_buy_slippage_bps=None,
        estimated_sell_slippage_bps=None,
        fillable_notional_within_slippage_cap=None,
        movement_persistence_score=None,
        volatility_pct=3.2,
        volume_24h=500.0,
        quote_volume_24h=60_000.0,
        liquidity_units=1200.0,
        spread_pct=0.15,
        movement_type=MovementType.SPIKE,
        last_price=350_000.0,
        change_pct=2.1,
        detected_at=datetime.now(timezone.utc),
        historical_confidence=1.0,
        volatility_score=0.32,
        volume_score=0.50,
        liquidity_score=0.80,
        spread_score=0.70,
        repetition_score=0.20,
        movement_multiplier=1.15,
        technical_signal_id="sig-abc-123",
    )
    defaults.update(overrides)
    return Opportunity(**defaults)


def _session_and_workspace_patches(monkeypatch, config=None):
    """Apply common monkeypatches for authenticated access."""
    monkeypatch.setattr(routes.settings, "admin_token", "tok")

    if config is None:
        config = AppConfig(enabled_pairs=["BTC_BRL"])

    async def _legacy():
        return UserSession(
            user_id="u-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def _resolve(session_info, workspace_id):
        return _make_workspace(), config

    monkeypatch.setattr(routes, "legacy_admin_session", _legacy)
    monkeypatch.setattr(routes, "resolve_workspace_context", _resolve)


# ---------------------------------------------------------------------------
# /api/dashboard/stats contract
# ---------------------------------------------------------------------------

def test_dashboard_stats_contract_shape(monkeypatch):
    """DashboardStats must include all required KPI fields."""
    opp = _fake_opportunity()
    routes.update_state([opp], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/dashboard/stats", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    body = resp.json()
    required_keys = {
        "total_opportunities",
        "active_opportunities",
        "monitored_pairs",
        "total_volume_24h",
        "best_score",
        "exchanges_online",
        "arbitrage_opportunities",
        "last_scan",
    }
    assert required_keys <= set(body.keys())


def test_dashboard_stats_uses_snapshot_fallback_when_no_local_state(monkeypatch):
    """When _current_opportunities is empty, dashboard falls back to DB snapshots."""
    routes.update_state([], None)  # no local state
    _session_and_workspace_patches(monkeypatch)

    fake_snap = _fake_opportunity(id="snap-1").model_dump(mode="json")

    async def _snapshots():
        return [fake_snap]

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _snapshots)

    client = _create_client()
    resp = client.get("/api/dashboard/stats", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_opportunities"] >= 1


# ---------------------------------------------------------------------------
# /api/opportunities contract
# ---------------------------------------------------------------------------

def test_opportunities_contract_includes_technical_fields(monkeypatch):
    """Each opportunity must include technical and executability contract fields."""
    opp = _fake_opportunity()
    routes.update_state([opp], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/opportunities", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    item = items[0]
    assert "technical_score" in item
    assert "score_version" in item
    assert "technical_signal_id" in item
    assert "executability_version" in item
    assert "movement_version" in item
    assert "profile_version" in item
    assert "executability_score" in item
    assert "executability_band" in item
    assert "interesting_signal" in item
    assert "operable_signal" in item
    assert "bid_notional_top_n" in item
    assert "ask_notional_top_n" in item
    assert "total_notional_top_n" in item
    assert "estimated_buy_slippage_bps" in item
    assert "estimated_sell_slippage_bps" in item
    assert "fillable_notional_within_slippage_cap" in item
    assert "movement_persistence_score" in item
    assert item["score_version"] == "v1"


def test_opportunities_filter_by_min_score(monkeypatch):
    """min_score filter is applied on workspace-projected score."""
    low = _fake_opportunity(
        id="low", score=20.0,
        volatility_score=0.01, volume_score=0.01, liquidity_score=0.01,
        spread_score=0.01, repetition_score=0.01, movement_multiplier=1.0,
    )
    high = _fake_opportunity(
        id="high", score=90.0,
        volatility_score=0.90, volume_score=0.90, liquidity_score=0.90,
        spread_score=0.90, repetition_score=0.90, movement_multiplier=1.15,
    )
    routes.update_state([low, high], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/opportunities?min_score=50", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert "high" in ids
    assert "low" not in ids


def test_opportunities_can_sort_by_executability(monkeypatch):
    lower_exec = _fake_opportunity(id="lower-exec", executability_score=42.0, executability_band="fair")
    higher_exec = _fake_opportunity(id="higher-exec", executability_score=78.0, executability_band="good")
    routes.update_state([lower_exec, higher_exec], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/opportunities?sort_by=executability", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert ids[:2] == ["higher-exec", "lower-exec"]


def test_opportunities_can_filter_operable_only(monkeypatch):
    inoperable = _fake_opportunity(id="inoperable", operable_signal=False, executability_score=35.0)
    operable = _fake_opportunity(id="operable", operable_signal=True, executability_score=75.0)
    routes.update_state([inoperable, operable], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/opportunities?operable_only=true", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    ids = [o["id"] for o in resp.json()]
    assert ids == ["operable"]


def test_opportunity_detail_returns_single_item(monkeypatch):
    opp = _fake_opportunity(id="detail-1")
    routes.update_state([opp], datetime.now(timezone.utc))
    _session_and_workspace_patches(monkeypatch)

    async def _no_snapshots():
        return []

    monkeypatch.setattr(routes, "read_opportunity_snapshots", _no_snapshots)

    client = _create_client()
    resp = client.get("/api/opportunities/detail-1", headers={"X-Admin-Token": "tok"})
    assert resp.status_code == 200
    assert resp.json()["id"] == "detail-1"


# ---------------------------------------------------------------------------
# /api/health contract
# ---------------------------------------------------------------------------

def test_health_contract_shape(monkeypatch):
    """Health endpoint must include mode, scanner_state, and scanner fields."""
    routes.update_state([], None)
    routes.set_scan_config(AppConfig())

    async def _state():
        return None

    monkeypatch.setattr(routes, "get_scanner_runtime_state", _state)

    client = _create_client()
    resp = client.get("/api/health")

    assert resp.status_code == 200
    body = resp.json()
    required = {"status", "mode", "last_scan", "opportunities_count", "scanner", "scanner_state", "websocket_connections"}
    assert required <= set(body.keys())


def test_health_mode_reflects_scanner_presence(monkeypatch):
    """mode=scanner when local scan exists, api_only otherwise."""
    async def _state():
        return {"last_success_at": "2025-01-01T00:00:00"}

    monkeypatch.setattr(routes, "get_scanner_runtime_state", _state)

    # With local scanner
    routes.update_state([], datetime.now(timezone.utc))
    client = _create_client()
    body = client.get("/api/health").json()
    assert body["mode"] == "scanner"

    # Without local scanner
    routes.update_state([], None)
    body2 = client.get("/api/health").json()
    assert body2["mode"] == "api_only"


# ---------------------------------------------------------------------------
# /api/config contract — new telegram fields
# ---------------------------------------------------------------------------

def test_config_contract_includes_telegram_policy_fields(monkeypatch):
    """Config response must include the new telegram_alert_* fields."""
    config = AppConfig(
        telegram_alert_threshold=75.0,
        telegram_alert_cooldown_seconds=600,
        telegram_alert_types=["high_score"],
    )
    _session_and_workspace_patches(monkeypatch, config=config)

    client = _create_client()
    resp = client.get("/api/config", headers={"X-Admin-Token": "tok"})

    assert resp.status_code == 200
    body = resp.json()["config"]
    assert body["telegram_alert_threshold"] == 75.0
    assert body["telegram_alert_cooldown_seconds"] == 600
    assert body["telegram_alert_types"] == ["high_score"]


def test_config_update_accepts_telegram_policy_fields(monkeypatch):
    """PUT /api/config accepts the new telegram_alert_* fields."""
    _session_and_workspace_patches(monkeypatch)

    saved = {}

    async def _save(workspace_id, config):
        saved["config"] = config

    async def _audit(*a, **kw):
        pass

    monkeypatch.setattr(routes, "save_workspace_config", _save)
    monkeypatch.setattr(routes, "record_audit_event", _audit)

    client = _create_client()
    resp = client.put(
        "/api/config",
        headers={"X-Admin-Token": "tok"},
        json={
            "telegram_alert_threshold": 80.0,
            "telegram_alert_cooldown_seconds": 300,
            "telegram_alert_types": ["arbitrage"],
        },
    )

    assert resp.status_code == 200
    assert saved["config"].telegram_alert_threshold == 80.0
    assert saved["config"].telegram_alert_cooldown_seconds == 300
    assert saved["config"].telegram_alert_types == ["arbitrage"]


# ---------------------------------------------------------------------------
# Opportunity model contract
# ---------------------------------------------------------------------------

def test_opportunity_model_round_trips_technical_fields():
    """Opportunity pydantic model correctly serializes new P2 fields."""
    opp = _fake_opportunity()
    data = opp.model_dump(mode="json")
    assert data["technical_score"] == 68.3
    assert data["score_version"] == "v1"
    assert data["executability_version"] == "v1"
    assert data["movement_version"] == "v1"
    assert data["profile_version"] == "v1"
    assert data["technical_signal_id"] == "sig-abc-123"
    assert "executability_score" in data
    assert "executability_band" in data
    assert "interesting_signal" in data
    assert "operable_signal" in data

    restored = Opportunity(**data)
    assert restored.technical_score == opp.technical_score
    assert restored.score_version == opp.score_version
    assert restored.executability_version == opp.executability_version
    assert restored.movement_version == opp.movement_version
    assert restored.profile_version == opp.profile_version
    assert restored.technical_signal_id == opp.technical_signal_id
