from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.models.schemas import AppConfig
from app.services.auth import UserSession


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_config_requires_admin_token(monkeypatch):
    monkeypatch.setattr(routes.settings, "admin_token", "secret-token")
    routes.set_scan_config(AppConfig())

    client = create_test_client()
    response = client.get("/api/config")

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
            None,
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
            type("Workspace", (), {"id": "workspace-1"})(),
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
