"""
WebSocket 连接管理器
基于 FastAPI WebSocket + 内存频道的实时推送
"""
import json
import logging
from typing import Dict, List, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # channel -> set of WebSocket
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket):
        """接受连接并加入频道"""
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel} (total: {len(self._connections[channel])})")

    def disconnect(self, channel: str, websocket: WebSocket):
        """断开连接"""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]
            logger.info(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, channel: str, message: Any):
        """向指定频道广播消息"""
        if channel not in self._connections:
            return
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead: List[WebSocket] = []
        for ws in self._connections[channel]:
            try:
                await ws.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)

    def get_channels(self) -> List[str]:
        return list(self._connections.keys())

    def get_connections_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


# 全局连接管理器
connection_manager = ConnectionManager()


async def create_ws_endpoint(channel: str = "default"):
    """
    创建 WebSocket 端点工厂
    使用示例：
        @app.websocket("/ws/{channel}")
        async def ws_handler(websocket: WebSocket, channel: str):
            await ws_endpoint(websocket, channel)
    """

    async def ws_endpoint(websocket: WebSocket, ch: str = channel):
        await connection_manager.connect(ch, websocket)
        try:
            while True:
                # 保持连接，接收心跳
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            connection_manager.disconnect(ch, websocket)

    return ws_endpoint
