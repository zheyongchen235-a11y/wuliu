"""WebSocket 进度推送: /ws/scheduling/{task_id}."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.ws import ws_manager

router = APIRouter()


@router.websocket("/ws/scheduling/{task_id}")
async def scheduling_progress(ws: WebSocket, task_id: str):
    await ws_manager.connect(task_id, ws)
    try:
        while True:
            # 客户端可发送心跳/订阅指令，这里仅维持连接
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(task_id, ws)
