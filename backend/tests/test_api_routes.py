from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.models.schemas import AppConfig, Exchange, ExchangeCredentialValidationResult, Opportunity
from app.services.auth import UserSession


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def make_workspace(*, role: str = "owner", **overrides):
    payload = {
        "id": "workspace-1",
        "slug": "desk",
        "name": "Desk",
        "role": role,
        "is_active": True,
    }
    payload.update(overrides)
    return type("Workspace", (), payload)()


def make_opportunity(**overrides) -> Opportunity:
    payload = {
        "id": "opp-1",
        "exchange": Exchange.NOVADAX,
        "pair": "BTC_BRL",
        "score": 74.0,
        "technical_score": 70.0,
        "executability_score": 78.0,
        "executability_band": "good",
        "interesting_signal": True,
        "operable_signal": True,
        "estimated_trade_margin_pct": 1.2,
        "operational_friction_pct": 0.18,
        "estimated_net_trade_edge_pct": 1.02,
        "trade_margin_score": 51.0,
        "opportunity_type": "trade",
        "volatility_pct": 4.0,
        "volume_24h": 20.0,
        "quote_volume_24h": 300000.0,
        "liquidity_units": 10000.0,
        "bid_notional_top_n": 20000.0,
        "ask_notional_top_n": 21000.0,
        "total_notional_top_n": 41000.0,
        "spread_pct": 0.08,
        "estimated_buy_slippage_bps": 4.0,
        "estimated_sell_slippage_bps": 5.0,
        "fillable_notional_within_slippage_cap": 3000.0,
        "baseline_order_notional_brl": 1000.0,
        "movement_type": "strong_range",
        "movement_regime": "trend_continuation",
        "movement_persistence_score": 0.6,
        "last_price": 300000.0,
        "change_pct": 1.4,
    }
    payload.update(overrides)
    return Opportunity(**payload)


def test_config_requires_admin_token(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    routes.set_scan_config(AppConfig())

    client = create_test_client()
    response = client.get("/api/config")

    assert response.status_code == 401


def test_dashboard_requires_authenticated_session(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    client = create_test_client()
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_endpoint_returns_opportunities_and_stats_in_one_payload(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL"])

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    routes.update_state([make_opportunity()], None)

    client = create_test_client()
    response = client.get("/api/dashboard", headers={"X-Admin-Token": "secret-token"})

    body = response.json()
    assert response.status_code == 200
    assert body["stats"]["total_opportunities"] == 1
    assert body["stats"]["trade_opportunities"] == 1
    assert body["opportunities"][0]["opportunity_type"] == "trade"


def test_dashboard_summary_returns_lightweight_shortlist(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL", "DOGE_BRL"])

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    routes.update_state(
        [
            make_opportunity(id="trade-1", pair="BTC_BRL", opportunity_type="trade", operable_signal=True),
            make_opportunity(
                id="avoid-1",
                pair="DOGE_BRL",
                opportunity_type="avoid",
                operable_signal=False,
                executability_score=20.0,
                score=95.0,
            ),
        ],
        None,
    )

    client = create_test_client()
    response = client.get("/api/dashboard/summary", headers={"X-Admin-Token": "secret-token"})

    body = response.json()
    assert response.status_code == 200
    assert body["stats"]["total_opportunities"] == 1
    assert body["shortlist"][0]["id"] == "trade-1"
    assert "klines" not in body["shortlist"][0]


def test_dashboard_excludes_technical_noise_by_default(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL", "DOGE_BRL"])

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    routes.update_state(
        [
            make_opportunity(id="trade-1", pair="BTC_BRL", opportunity_type="trade", operable_signal=True),
            make_opportunity(
                id="avoid-1",
                pair="DOGE_BRL",
                opportunity_type="avoid",
                operable_signal=False,
                score=99.0,
                estimated_net_trade_edge_pct=1.0,
            ),
        ],
        None,
    )

    client = create_test_client()
    response = client.get("/api/dashboard", headers={"X-Admin-Token": "secret-token"})

    body = response.json()
    assert response.status_code == 200
    assert [item["id"] for item in body["opportunities"]] == ["trade-1"]
    assert body["opportunities"][0]["pipeline_status"] == "operational_opportunity"


def test_opportunities_can_include_technical_records_explicitly(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL", "DOGE_BRL"])

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    routes.update_state(
        [
            make_opportunity(id="trade-1", pair="BTC_BRL", opportunity_type="trade", operable_signal=True),
            make_opportunity(
                id="avoid-1",
                pair="DOGE_BRL",
                opportunity_type="avoid",
                operable_signal=False,
                score=99.0,
                estimated_net_trade_edge_pct=1.0,
            ),
        ],
        None,
    )

    client = create_test_client()
    default_response = client.get("/api/opportunities", headers={"X-Admin-Token": "secret-token"})
    technical_response = client.get("/api/opportunities?include_technical=true", headers={"X-Admin-Token": "secret-token"})

    assert [item["id"] for item in default_response.json()] == ["trade-1"]
    assert {item["id"] for item in technical_response.json()} == {"trade-1", "avoid-1"}
    assert next(item for item in technical_response.json() if item["id"] == "avoid-1")["pipeline_status"] == "blocked_signal"


def test_opportunities_shortlist_excludes_avoid_signals(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL", "DOGE_BRL"])

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    routes.update_state(
        [
            make_opportunity(id="trade-1", pair="BTC_BRL", opportunity_type="trade", operable_signal=True),
            make_opportunity(
                id="avoid-1",
                pair="DOGE_BRL",
                opportunity_type="avoid",
                operable_signal=False,
                interesting_signal=False,
                score=10.0,
                executability_score=10.0,
                trade_margin_score=0.0,
                estimated_net_trade_edge_pct=-5.0,
                quote_volume_24h=10.0,
                bid_notional_top_n=0.0,
                ask_notional_top_n=0.0,
                total_notional_top_n=0.0,
                fillable_notional_within_slippage_cap=0.0,
                estimated_buy_slippage_bps=None,
                estimated_sell_slippage_bps=None,
                movement_regime="illiquid_spike",
            ),
        ],
        None,
    )

    client = create_test_client()
    response = client.get("/api/opportunities/shortlist", headers={"X-Admin-Token": "secret-token"})

    body = response.json()
    assert response.status_code == 200
    assert [item["id"] for item in body] == ["trade-1"]


def test_submit_signal_feedback_persists_workspace_context(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    captured = []

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(id="workspace-1", role="owner"), AppConfig(enabled_pairs=["BTC_BRL"])

    async def fake_create_signal_feedback(**kwargs):
        captured.append(kwargs)
        return {
            "id": "feedback-1",
            **kwargs,
            "created_at": "2026-05-07T00:00:00",
        }

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "create_signal_feedback", fake_create_signal_feedback)

    client = create_test_client()
    response = client.post(
        "/api/signals/feedback",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "signal_id": "signal-1",
            "opportunity_id": "opp-1",
            "feedback_label": "good_margin",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["id"] == "feedback-1"
    assert captured[0]["user_id"] == "user-1"
    assert captured[0]["workspace_id"] == "workspace-1"
    assert captured[0]["feedback_label"] == "good_margin"


def test_history_requires_authenticated_session(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    client = create_test_client()
    response = client.get("/api/history")

    assert response.status_code == 401


def test_history_passes_visibility_filter_to_persistence(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    captured: list[str] = []

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["BTC_BRL"])

    async def fake_get_history(*args, visibility="all", **kwargs):
        captured.append(visibility)
        return []

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "get_history", fake_get_history)

    client = create_test_client()
    response = client.get("/api/history?visibility=technical", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 200
    assert captured == ["technical"]


def test_near_misses_diagnostic_endpoint_returns_compact_events(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    captured: list[dict] = []

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["SOL_BRL"])

    async def fake_get_near_misses(**kwargs):
        captured.append(kwargs)
        return [
            {
                "cycle_id": "cycle-1",
                "exchange": "novadax",
                "pair": "SOL_BRL",
                "stage": "promotion",
                "status": "near_miss",
                "reason": "candidate_limit_lower_priority",
                "details": {"distance_to_selected_score": 2.5},
                "created_at": "2026-05-08T10:00:00",
            }
        ]

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "get_near_misses", fake_get_near_misses)

    client = create_test_client()
    response = client.get(
        "/api/diagnostics/near-misses?exchange=novadax&pair=SOL_BRL&from=2026-05-08T10:00:00Z&to=2026-05-08T11:00:00Z",
        headers={"X-Admin-Token": "secret-token"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["workspace_id"] == "workspace-1"
    assert body["count"] == 1
    assert body["near_misses"][0]["reason"] == "candidate_limit_lower_priority"
    assert captured[0]["exchange"] == "novadax"
    assert captured[0]["pair"] == "SOL_BRL"


def test_funnel_quality_endpoint_returns_compact_metrics(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    captured: list[dict] = []

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig(enabled_pairs=["SOL_BRL"])

    async def fake_get_funnel_quality_metrics(**kwargs):
        captured.append(kwargs)
        return {
            "workspace_id": kwargs["workspace_id"],
            "cycle_totals": {"cycles": 1, "total_pairs": 20, "alerts_sent": 0},
            "rates": {"light_candidate_rate": 0.2, "alert_send_rate": 0.0},
            "top_alert_block_reasons": [{"reason": "no_state_change", "count": 1}],
        }

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "get_funnel_quality_metrics", fake_get_funnel_quality_metrics)

    client = create_test_client()
    response = client.get(
        "/api/diagnostics/funnel-quality?exchange=novadax&pair=SOL_BRL&from=2026-05-08T10:00:00Z&to=2026-05-08T11:00:00Z",
        headers={"X-Admin-Token": "secret-token"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["workspace_id"] == "workspace-1"
    assert body["cycle_totals"]["cycles"] == 1
    assert body["top_alert_block_reasons"][0]["reason"] == "no_state_change"
    assert captured[0]["exchange"] == "novadax"
    assert captured[0]["pair"] == "SOL_BRL"


def test_config_hides_sensitive_fields(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            AppConfig(
                telegram_bot_token="bot-token",
                telegram_chat_id="chat-id",
                novadax_api_secret="hidden-secret",
            ),
        )

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)

    client = create_test_client()
    response = client.get("/api/config", headers={"X-Admin-Token": "secret-token"})

    body = response.json()
    assert response.status_code == 200
    assert body["config"]["telegram_bot_token"] == ""
    assert body["config"]["telegram_chat_id"] == ""
    assert body["config"]["novadax_api_secret"] == ""
    assert body["configured_secrets"]["telegram_bot_token"] is True
    assert body["configured_secrets"]["telegram_chat_id"] is True
    assert body["configured_secrets"]["novadax_api_secret"] is True


def test_update_config_preserves_existing_secret_on_blank(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_save_workspace_config(workspace_id, config):
        return None

    async def fake_audit(*args, **kwargs):
        return None

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    current_config = AppConfig(telegram_bot_token="persist-me", telegram_chat_id="chat-id")

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            current_config,
        )

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "save_workspace_config", fake_save_workspace_config)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)

    client = create_test_client()
    response = client.put(
        "/api/config",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "telegram_bot_token": "",
            "scan_interval_seconds": 45,
        },
    )

    assert response.status_code == 200
    assert response.json()["config"]["telegram_bot_token"] == ""
    assert response.json()["config"]["scan_interval_seconds"] == 45
    assert response.json()["configured_secrets"]["telegram_bot_token"] is True


def test_update_config_accepts_operational_profile_fields(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    saved_configs = []

    async def fake_save_workspace_config(workspace_id, config):
        saved_configs.append((workspace_id, config))
        return None

    async def fake_audit(*args, **kwargs):
        return None

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(role="owner"), AppConfig()

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "save_workspace_config", fake_save_workspace_config)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)

    client = create_test_client()
    response = client.put(
        "/api/config",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "trading_profile": "scalp",
            "order_notional_brl": 850,
            "max_entry_slippage_bps": 11,
            "max_exit_slippage_bps": 14,
            "min_quote_volume_brl": 120000,
            "telegram_operable_only": True,
        },
    )

    assert response.status_code == 200
    assert saved_configs[0][1].trading_profile == "scalp"
    assert saved_configs[0][1].telegram_operable_only is True


def test_health_includes_runtime_snapshot(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    routes.set_scan_config(AppConfig())
    routes.update_state([], None)

    async def fake_scanner_state():
        return None

    monkeypatch.setattr(routes, "get_scanner_runtime_state", fake_scanner_state)

    client = create_test_client()
    response = client.get("/api/health")

    body = response.json()
    assert response.status_code == 200
    assert "scanner" in body
    assert "last_scan_diagnostics" in body["scanner"]
    assert "scanner_state" in body
    assert "mode" in body
    assert "websocket_connections" in body


def test_admin_login_returns_bearer_token(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_bootstrap():
        return None

    async def fake_authenticate(username: str, password: str):
        if username == "admin" and password == "secret":
            return UserSession(
                user_id="user-1",
                username="admin",
                role="admin",
                auth_mode="database",
                token_version=3,
            )
        return None

    async def fake_audit(*args, **kwargs):
        return None

    async def fake_session_metadata(session_info: UserSession):
        return {
            "user_id": session_info.user_id,
            "username": session_info.username,
            "role": session_info.role,
            "auth_mode": session_info.auth_mode,
            "token_version": session_info.token_version,
            "password_last_changed_at": None,
            "workspaces": [],
        }

    monkeypatch.setattr(routes, "ensure_admin_bootstrap", fake_bootstrap)
    monkeypatch.setattr(routes, "authenticate_admin_credentials", fake_authenticate)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)
    monkeypatch.setattr(routes, "get_user_session_metadata", fake_session_metadata)

    client = create_test_client()
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "secret"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["session"]["username"] == "admin"


def test_admin_session_accepts_bearer_token(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_bootstrap():
        return None

    async def fake_authenticate(username: str, password: str):
        if username == "admin" and password == "secret":
            return UserSession(
                user_id="user-1",
                username="admin",
                role="admin",
                auth_mode="database",
                token_version=2,
            )
        return None

    async def fake_verify(token: str):
        if token == "signed-token":
            return UserSession(
                user_id="user-1",
                username="admin",
                role="admin",
                auth_mode="database",
                token_version=2,
            )
        return None

    async def fake_session_metadata(session_info: UserSession):
        return {
            "user_id": session_info.user_id,
            "username": session_info.username,
            "role": session_info.role,
            "auth_mode": session_info.auth_mode,
            "token_version": session_info.token_version,
            "password_last_changed_at": None,
            "workspaces": [],
        }

    async def fake_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(routes, "ensure_admin_bootstrap", fake_bootstrap)
    monkeypatch.setattr(routes, "authenticate_admin_credentials", fake_authenticate)
    monkeypatch.setattr(routes, "verify_access_token", fake_verify)
    monkeypatch.setattr(routes, "get_user_session_metadata", fake_session_metadata)
    monkeypatch.setattr(routes, "issue_access_token", lambda *args, **kwargs: "signed-token")
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)

    client = create_test_client()
    login_response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "secret"},
    )
    token = login_response.json()["access_token"]

    response = client.get("/api/admin/session", headers={"Authorization": f"Bearer {token}"})

    body = response.json()
    assert response.status_code == 200
    assert body["username"] == "admin"


def test_auth_refresh_returns_rotated_tokens(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")
    monkeypatch.setattr(routes.settings, "access_token_ttl_minutes", 480)
    monkeypatch.setattr(routes.settings, "refresh_token_ttl_days", 30)

    async def fake_verify_refresh(token: str):
        if token == "refresh-token":
            return UserSession(
                user_id="user-1",
                username="admin",
                role="admin",
                auth_mode="database",
                token_version=4,
            )
        return None

    async def fake_session_metadata(session_info: UserSession):
        return {
            "user_id": session_info.user_id,
            "username": session_info.username,
            "role": session_info.role,
            "auth_mode": session_info.auth_mode,
            "token_version": session_info.token_version,
            "password_last_changed_at": None,
            "must_change_password": False,
            "workspaces": [],
        }

    monkeypatch.setattr(routes, "verify_refresh_token", fake_verify_refresh)
    monkeypatch.setattr(routes, "issue_access_token", lambda *args, **kwargs: "new-access-token")
    monkeypatch.setattr(routes, "issue_refresh_token", lambda *args, **kwargs: "new-refresh-token")
    monkeypatch.setattr(routes, "get_user_session_metadata", fake_session_metadata)

    client = create_test_client()
    response = client.post("/api/auth/refresh", json={"refresh_token": "refresh-token"})

    body = response.json()
    assert response.status_code == 200
    assert body["access_token"] == "new-access-token"
    assert body["refresh_token"] == "new-refresh-token"
    assert body["refresh_expires_in_seconds"] == 30 * 24 * 3600


def test_config_requires_workspace_admin_role(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_verify(token: str):
        if token == "admin-token":
            return UserSession(
                user_id="user-2",
                username="admin-account",
                role="admin",
                auth_mode="database",
                token_version=1,
            )
        return None

    async def fake_resolve_workspace_context(session_info, workspace_id):
        assert session_info.role == "admin"
        return (
            make_workspace(role="member"),
            AppConfig(),
        )

    monkeypatch.setattr(routes, "verify_access_token", fake_verify)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)

    client = create_test_client()
    response = client.get("/api/config", headers={"Authorization": "Bearer admin-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Workspace admin role required"


def test_config_accepts_workspace_admin_role_even_for_member_session(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_verify(token: str):
        if token == "member-token":
            return UserSession(
                user_id="user-2",
                username="member-account",
                role="member",
                auth_mode="database",
                token_version=1,
            )
        return None

    async def fake_resolve_workspace_context(session_info, workspace_id):
        assert session_info.role == "member"
        return (
            make_workspace(role="admin"),
            AppConfig(telegram_bot_token="bot-token", telegram_chat_id="chat-id"),
        )

    monkeypatch.setattr(routes, "verify_access_token", fake_verify)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)

    client = create_test_client()
    response = client.get("/api/config", headers={"Authorization": "Bearer member-token"})

    assert response.status_code == 200
    assert response.json()["config"]["telegram_bot_token"] == ""
    assert response.json()["configured_secrets"]["telegram_bot_token"] is True


def test_users_endpoint_requires_workspace_owner_role(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_verify(token: str):
        if token == "member-token":
            return UserSession(
                user_id="user-2",
                username="workspace-admin",
                role="member",
                auth_mode="database",
                token_version=1,
            )
        return None

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="admin"),
            AppConfig(),
        )

    monkeypatch.setattr(routes, "verify_access_token", fake_verify)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)

    client = create_test_client()
    response = client.get("/api/users", headers={"Authorization": "Bearer member-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Workspace owner role required"


def test_available_pairs_endpoint_returns_aggregated_catalog(monkeypatch):
    async def fake_catalog(enabled_exchanges=None, force_refresh: bool = False):
        return {
            "generated_at": "2026-04-15T12:00:00+00:00",
            "expires_at": "2026-04-15T13:00:00+00:00",
            "pairs": [
                {
                    "pair": "BTC_BRL",
                    "display_name": "BTC/BRL",
                    "availability": {
                        "novadax": True,
                        "mercado_bitcoin": True,
                        "binance": True,
                    },
                },
                {
                    "pair": "POL_BRL",
                    "display_name": "POL/BRL",
                    "availability": {
                        "novadax": False,
                        "mercado_bitcoin": False,
                        "binance": True,
                    },
                },
            ],
        }

    monkeypatch.setattr(routes, "get_available_pairs_catalog", fake_catalog)

    client = create_test_client()
    response = client.get("/api/pairs/available")

    body = response.json()
    assert response.status_code == 200
    assert body["pairs"][0]["pair"] == "BTC_BRL"
    assert body["pairs"][1]["availability"]["binance"] is True


def test_available_pairs_endpoint_forwards_enabled_exchanges(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_catalog(enabled_exchanges=None, force_refresh: bool = False):
        captured["enabled_exchanges"] = enabled_exchanges
        captured["force_refresh"] = force_refresh
        return {
            "generated_at": "2026-04-15T12:00:00+00:00",
            "expires_at": "2026-04-15T13:00:00+00:00",
            "pairs": [],
            "provider_status": [],
        }

    monkeypatch.setattr(routes, "get_available_pairs_catalog", fake_catalog)

    client = create_test_client()
    response = client.get("/api/pairs/available?enabled_exchanges=novadax&enabled_exchanges=binance&force_refresh=true")

    assert response.status_code == 200
    assert captured["enabled_exchanges"] == [Exchange.NOVADAX, Exchange.BINANCE]
    assert captured["force_refresh"] is True


def test_pair_diagnostic_endpoint_returns_exchange_diagnostic(monkeypatch):
    async def fake_diagnostic(exchange, pair):
        return {
            "exchange": exchange,
            "pair": "LAB_BRL",
            "display_name": "LAB/BRL",
            "raw_symbol": "LAB_BRL",
            "exists_in_catalog": True,
            "overall_status": "ok",
            "checked_at": "2026-05-06T12:00:00",
            "checks": [
                {"name": "catalog", "status": "ok", "message": None, "details": {"returned_pairs": 10}},
                {"name": "ticker", "status": "ok", "message": None, "details": {}},
            ],
        }

    monkeypatch.setattr(routes, "get_pair_exchange_diagnostic", fake_diagnostic)

    client = create_test_client()
    response = client.get("/api/pairs/diagnostics/novadax/LAB_BRL")

    assert response.status_code == 200
    body = response.json()
    assert body["exchange"] == "novadax"
    assert body["pair"] == "LAB_BRL"
    assert body["overall_status"] == "ok"
    assert body["checks"][0]["name"] == "catalog"


def test_missed_signal_diagnostic_endpoint_returns_timeline(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_diagnostic(*, exchange, pair, from_time, to_time, **kwargs):
        assert exchange == "novadax"
        assert pair == "SOL_BRL"
        assert kwargs["workspace_id"] == "default"
        return {
            "exchange": exchange,
            "pair": pair,
            "from": from_time.isoformat(),
            "to": to_time.isoformat(),
            "status": "events_found",
            "final_state": "technical_signal_created",
            "root_cause_stage": "light_scan",
            "root_cause_reason": "candidate",
            "workspace_status": {"workspace_id": kwargs["workspace_id"]},
            "catalog_status": kwargs["catalog_status"],
            "message": "Linha do tempo encontrada para o par no intervalo.",
            "timeline": [
                {
                    "cycle_id": "cycle-1",
                    "stage": "light_scan",
                    "status": "candidate",
                    "reason": "candidate",
                    "created_at": from_time.isoformat(),
                }
            ],
            "cycle_summaries": [],
        }

    async def fake_pair_diagnostic(exchange, pair):
        return {
            "exchange": exchange,
            "pair": "SOL_BRL",
            "display_name": "SOL/BRL",
            "raw_symbol": "SOLBRL",
            "exists_in_catalog": True,
            "overall_status": "ok",
            "checked_at": "2026-05-07T10:00:00",
            "checks": [],
        }

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return make_workspace(id="default"), AppConfig()

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "get_missed_signal_diagnostic", fake_diagnostic)
    monkeypatch.setattr(routes, "get_pair_exchange_diagnostic", fake_pair_diagnostic)

    client = create_test_client()
    response = client.get(
        "/api/diagnostics/missed-signal?exchange=novadax&pair=SOL_BRL&from=2026-05-07T10:00:00Z&to=2026-05-07T11:00:00Z",
        headers={"X-Admin-Token": "secret-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "events_found"
    assert response.json()["timeline"][0]["stage"] == "light_scan"


def test_telegram_test_endpoint_uses_workspace_config_fallback(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    sent_payload: dict[str, str] = {}

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            AppConfig(telegram_bot_token="persisted-bot", telegram_chat_id="persisted-chat"),
        )

    async def fake_send_test_message(*, token: str, chat_id: str, workspace_name: str, actor_username: str):
        sent_payload.update(
            {
                "token": token,
                "chat_id": chat_id,
                "workspace_name": workspace_name,
                "actor_username": actor_username,
            }
        )
        return True

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "send_telegram_test_message", fake_send_test_message)

    client = create_test_client()
    response = client.post(
        "/api/config/telegram/test",
        headers={"X-Admin-Token": "secret-token"},
        json={"telegram_bot_token": "", "telegram_chat_id": ""},
    )

    assert response.status_code == 200
    assert response.json()["delivered"] is True
    assert sent_payload == {
        "token": "persisted-bot",
        "chat_id": "persisted-chat",
        "workspace_name": "Desk",
        "actor_username": "admin",
    }


def test_invite_preview_returns_public_metadata(monkeypatch):
    async def fake_preview(code: str):
        assert code == "invite-code"
        return {
            "code": code,
            "email": "convite@example.com",
            "workspace_name": "Desk",
            "organization_name": "Org One",
            "role": "member",
            "status": "pending",
            "expires_at": "2026-04-22T12:00:00+00:00",
        }

    monkeypatch.setattr(routes, "get_invite_preview", fake_preview)

    client = create_test_client()
    response = client.get("/api/invites/invite-code")

    assert response.status_code == 200
    assert response.json()["organization_name"] == "Org One"


def test_invite_accept_returns_tokens_and_session(monkeypatch):
    monkeypatch.setattr(routes.settings, "access_token_ttl_minutes", 480)
    monkeypatch.setattr(routes.settings, "refresh_token_ttl_days", 30)

    async def fake_accept(code: str, email: str, password: str):
        assert code == "invite-code"
        assert email == "novo@example.com"
        assert password == "super-secure-123"
        return UserSession(
            user_id="user-9",
            username="novo",
            role="member",
            auth_mode="database",
            token_version=0,
        )

    async def fake_session_metadata(session_info: UserSession):
        return {
            "user_id": session_info.user_id,
            "username": session_info.username,
            "email": "novo@example.com",
            "role": session_info.role,
            "auth_mode": session_info.auth_mode,
            "token_version": session_info.token_version,
            "password_last_changed_at": None,
            "must_change_password": False,
            "onboarding_completed_at": None,
            "organization": {
                "id": "org-1",
                "name": "Org One",
                "slug": "org-one",
                "plan": "trial",
                "stripe_customer_id": None,
                "subscription_status": "trialing",
                "trial_ends_at": None,
            },
            "workspaces": [
                {
                    "id": "workspace-1",
                    "slug": "desk",
                    "name": "Desk",
                    "role": "member",
                    "is_active": True,
                }
            ],
        }

    monkeypatch.setattr(routes, "accept_invite", fake_accept)
    monkeypatch.setattr(routes, "issue_access_token", lambda *_args, **_kwargs: "issued-access")
    monkeypatch.setattr(routes, "issue_refresh_token", lambda *_args, **_kwargs: "issued-refresh")
    monkeypatch.setattr(routes, "get_user_session_metadata", fake_session_metadata)

    client = create_test_client()
    response = client.post(
        "/api/invites/accept",
        json={
            "code": "invite-code",
            "email": "novo@example.com",
            "password": "super-secure-123",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["access_token"] == "issued-access"
    assert body["refresh_token"] == "issued-refresh"
    assert body["session"]["organization"]["name"] == "Org One"


def test_workspace_status_returns_session_projection(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    async def fake_verify(token: str):
        if token == "member-token":
            return UserSession(
                user_id="user-2",
                username="member",
                role="member",
                auth_mode="database",
                token_version=1,
            )
        return None

    async def fake_resolve_workspace_context(session_info, workspace_id):
        assert session_info.user_id == "user-2"
        assert workspace_id == "workspace-1"
        return type("Workspace", (), {"id": "workspace-1", "name": "Desk"})(), AppConfig()

    async def fake_workspace_status(*, session_info, workspace, config):
        assert session_info.username == "member"
        assert workspace.id == "workspace-1"
        return {
            "workspace": {
                "id": "workspace-1",
                "slug": "desk",
                "name": "Desk",
                "role": "member",
                "is_active": True,
            },
            "organization": {
                "id": "org-1",
                "name": "Org One",
                "slug": "org-one",
                "plan": "trial",
                "stripe_customer_id": None,
                "subscription_status": "trialing",
                "trial_ends_at": None,
            },
            "configured_pairs_count": 3,
            "enabled_exchange_count": 2,
            "telegram_configured": True,
            "exchange_credentials_configured": {
                "novadax": False,
                "mercado_bitcoin": False,
                "binance": True,
            },
            "onboarding_completed_at": None,
        }

    monkeypatch.setattr(routes, "verify_access_token", fake_verify)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "build_workspace_status_response", fake_workspace_status)

    client = create_test_client()
    response = client.get(
        "/api/workspace/status",
        headers={
            "Authorization": "Bearer member-token",
            "X-Workspace-Id": "workspace-1",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["workspace"]["name"] == "Desk"
    assert body["configured_pairs_count"] == 3
    assert body["exchange_credentials_configured"]["binance"] is True


def test_update_config_requests_immediate_scan_refresh(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    refresh_calls: list[str] = []
    audit_calls: list[str] = []

    async def fake_save_workspace_config(workspace_id, config):
        return None

    async def fake_audit(*args, **kwargs):
        audit_calls.append("called")
        return None

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    current_config = AppConfig(telegram_bot_token="persist-me", telegram_chat_id="chat-id")

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            current_config,
        )

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "save_workspace_config", fake_save_workspace_config)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)
    monkeypatch.setattr(routes, "request_scan_refresh", lambda: refresh_calls.append("called"))

    client = create_test_client()
    response = client.put(
        "/api/config",
        headers={"X-Admin-Token": "secret-token"},
        json={
            "telegram_bot_token": "",
            "scan_interval_seconds": 45,
        },
    )

    assert response.status_code == 200
    assert refresh_calls == ["called"]
    assert audit_calls == ["called"]


def test_update_config_can_skip_audit_for_autosave(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    refresh_calls: list[str] = []
    audit_calls: list[str] = []

    async def fake_save_workspace_config(workspace_id, config):
        return None

    async def fake_audit(*args, **kwargs):
        audit_calls.append("called")
        return None

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    current_config = AppConfig(telegram_bot_token="persist-me", telegram_chat_id="chat-id")

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            current_config,
        )

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "save_workspace_config", fake_save_workspace_config)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)
    monkeypatch.setattr(routes, "request_scan_refresh", lambda: refresh_calls.append("called"))

    client = create_test_client()
    response = client.put(
        "/api/config",
        headers={
            "X-Admin-Token": "secret-token",
            "X-Config-Audit-Mode": "skip",
        },
        json={
            "telegram_enabled": True,
            "scan_interval_seconds": 45,
        },
    )

    assert response.status_code == 200
    assert refresh_calls == ["called"]
    assert audit_calls == []


def test_validate_exchange_credentials_endpoint_returns_exchange_states(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")

    async def fake_legacy_session():
        return UserSession(
            user_id="user-1",
            username="admin",
            role="admin",
            auth_mode="legacy_token",
            token_version=0,
        )

    async def fake_resolve_workspace_context(session_info, workspace_id):
        return (
            make_workspace(role="owner"),
            AppConfig(),
        )

    async def fake_validate(config: AppConfig):
        return [
            ExchangeCredentialValidationResult(
                exchange=Exchange.BINANCE,
                state="valid",
                checked_at="2026-04-15T12:00:00+00:00",
                can_trade=True,
                message="Permissions ok",
            ),
            ExchangeCredentialValidationResult(
                exchange=Exchange.NOVADAX,
                state="missing",
                checked_at="2026-04-15T12:00:00+00:00",
                can_trade=None,
                message="Credentials not configured",
            ),
        ]

    async def fake_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(routes, "legacy_admin_session", fake_legacy_session)
    monkeypatch.setattr(routes, "resolve_workspace_context", fake_resolve_workspace_context)
    monkeypatch.setattr(routes, "validate_exchange_credentials", fake_validate)
    monkeypatch.setattr(routes, "record_audit_event", fake_audit)

    client = create_test_client()
    response = client.post(
        "/api/config/validate-exchanges",
        headers={"X-Admin-Token": "secret-token"},
        json={"binance_api_key": "abc", "binance_api_secret": "xyz"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["results"][0]["exchange"] == "binance"
    assert body["results"][0]["state"] == "valid"
    assert body["results"][1]["state"] == "missing"
