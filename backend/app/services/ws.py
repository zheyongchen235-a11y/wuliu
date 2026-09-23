"""WebSocket 进度推送管理器。"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class WSManager:
    """每个 task_id 维护一组 WebSocket 连接。"""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, task_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[task_id].add(ws)

    async def disconnect(self, task_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[task_id].discard(ws)
            if not self._connections[task_id]:
                self._connections.pop(task_id, None)

    async def broadcast(self, task_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            conns = list(self._connections.get(task_id, ()))
        if not conns:
            return
        message = {**payload, "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat()}
        text = json.dumps(message, default=str, ensure_ascii=False)
        await asyncio.gather(*[self._safe_send(ws, text) for ws in conns], return_exceptions=True)

    @staticmethod
    async def _safe_send(ws: WebSocket, text: str) -> None:
        try:
            await ws.send_text(text)
        except Exception:
            pass


ws_manager = WSManager()
