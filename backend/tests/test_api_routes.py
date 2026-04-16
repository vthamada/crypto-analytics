from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.models.schemas import AppConfig, Exchange, ExchangeCredentialValidationResult
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


def test_history_requires_authenticated_session(monkeypatch):
    monkeypatch.setattr(routes.settings, "auth_secret_key", "signing-key")

    client = create_test_client()
    response = client.get("/api/history")

    assert response.status_code == 401


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
    assert body["telegram_bot_token"] == ""
    assert body["telegram_chat_id"] == ""
    assert body["novadax_api_secret"] == ""


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
    assert response.json()["telegram_bot_token"] == ""
    assert response.json()["scan_interval_seconds"] == 45


def test_health_includes_runtime_snapshot(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    routes.set_scan_config(AppConfig())
    routes.update_state([], None)

    client = create_test_client()
    response = client.get("/api/health")

    body = response.json()
    assert response.status_code == 200
    assert "scanner" in body
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
    assert response.json()["telegram_bot_token"] == ""


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
    async def fake_catalog():
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
