from __future__ import annotations

from collections import defaultdict
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect, status

from app.services.auth import (
    legacy_admin_session,
    get_workspace_for_user,
    validate_legacy_admin_token,
    verify_access_token,
)
from app.services.persistence import DEFAULT_WORKSPACE_ID

logger = logging.getLogger(__name__)


class WebSocketAuthorizationError(Exception):
    def __init__(self, *, reason: str, code: int = status.WS_1008_POLICY_VIOLATION) -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self._connections_by_workspace: dict[str, list[WebSocket]] = defaultdict(list)
        self._workspace_by_connection: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, workspace_id: str) -> None:
        await websocket.accept()
        self._connections_by_workspace[workspace_id].append(websocket)
        self._workspace_by_connection[websocket] = workspace_id
        logger.info("websocket_connected workspace_id=%s total=%s", workspace_id, self.connection_count)

    def disconnect(self, websocket: WebSocket) -> None:
        workspace_id = self._workspace_by_connection.pop(websocket, None)
        if workspace_id is None:
            return

        connections = self._connections_by_workspace.get(workspace_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self._connections_by_workspace.pop(workspace_id, None)
        logger.info("websocket_disconnected workspace_id=%s total=%s", workspace_id, self.connection_count)

    async def broadcast_workspace(self, workspace_id: str, data: dict) -> None:
        """Send data only to connections subscribed to the target workspace."""
        connections = list(self._connections_by_workspace.get(workspace_id, []))
        if not connections:
            return

        message = json.dumps(data, default=str)
        disconnected = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return sum(len(connections) for connections in self._connections_by_workspace.values())


manager = ConnectionManager()


async def authenticate_websocket_connection(*, token: str, workspace_id: str) -> str:
    effective_token = token.strip()
    effective_workspace_id = workspace_id.strip()

    if not effective_token:
        raise WebSocketAuthorizationError(reason="Authentication required")
    if not effective_workspace_id:
        raise WebSocketAuthorizationError(reason="Workspace selection required")

    session_info = await verify_access_token(effective_token)
    if session_info is None:
        if validate_legacy_admin_token(effective_token):
            session_info = await legacy_admin_session()
        else:
            raise WebSocketAuthorizationError(reason="Invalid credentials")

    if session_info.user_id == "legacy-admin":
        if effective_workspace_id != DEFAULT_WORKSPACE_ID:
            raise WebSocketAuthorizationError(reason="Workspace access denied")
        return effective_workspace_id

    workspace = await get_workspace_for_user(session_info.user_id, effective_workspace_id)
    if workspace is None:
        raise WebSocketAuthorizationError(reason="Workspace access denied")

    return effective_workspace_id


async def websocket_endpoint(websocket: WebSocket) -> None:
    try:
        workspace_id = await authenticate_websocket_connection(
            token=websocket.query_params.get("token", ""),
            workspace_id=websocket.query_params.get("workspace_id", ""),
        )
    except WebSocketAuthorizationError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await manager.connect(websocket, workspace_id)
    try:
        while True:
            # Keep connection alive, handle client messages if needed
            data = await websocket.receive_text()
            # Client can send ping/config updates
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
