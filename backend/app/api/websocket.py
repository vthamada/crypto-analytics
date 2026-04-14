from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, data: dict) -> None:
        """Send data to all connected clients."""
        if not self._connections:
            return

        message = json.dumps(data, default=str)
        disconnected = []

        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
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
