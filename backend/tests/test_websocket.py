from __future__ import annotations

import asyncio
import json

import pytest

from app.api import websocket
from app.services.auth import UserSession


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, message: str) -> None:
        self.messages.append(message)


def test_connection_manager_broadcasts_only_to_target_workspace():
    async def run_test():
        manager = websocket.ConnectionManager()
        ws_default = FakeWebSocket()
        ws_research = FakeWebSocket()

        await manager.connect(ws_default, "default")
        await manager.connect(ws_research, "research")
        await manager.broadcast_workspace(
            "research",
            {"type": "opportunities_update", "count": 1, "data": []},
        )

        assert ws_default.accepted is True
        assert ws_research.accepted is True
        assert ws_default.messages == []
        assert len(ws_research.messages) == 1
        assert json.loads(ws_research.messages[0])["count"] == 1
        assert manager.connection_count == 2
        assert manager.workspace_ids == {"default", "research"}

        manager.disconnect(ws_default)
        manager.disconnect(ws_research)
        assert manager.connection_count == 0
        assert manager.workspace_ids == set()

    asyncio.run(run_test())


def test_authenticate_websocket_connection_requires_workspace_membership(monkeypatch):
    async def fake_verify_access_token(token: str):
        if token == "member-token":
            return UserSession(
                user_id="user-1",
                username="member",
                role="member",
                auth_mode="database",
                token_version=1,
            )
        return None

    async def fake_get_workspace_for_user(user_id: str, workspace_id: str):
        if user_id == "user-1" and workspace_id == "workspace-1":
            return object()
        return None

    monkeypatch.setattr(websocket, "verify_access_token", fake_verify_access_token)
    monkeypatch.setattr(websocket, "get_workspace_for_user", fake_get_workspace_for_user)

    granted_workspace = asyncio.run(
        websocket.authenticate_websocket_connection(token="member-token", workspace_id="workspace-1")
    )

    assert granted_workspace == "workspace-1"

    with pytest.raises(websocket.WebSocketAuthorizationError, match="Workspace access denied"):
        asyncio.run(
            websocket.authenticate_websocket_connection(token="member-token", workspace_id="workspace-2")
        )