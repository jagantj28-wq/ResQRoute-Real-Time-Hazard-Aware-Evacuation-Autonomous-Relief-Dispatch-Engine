from fastapi import WebSocket
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger('resqroute.ws')

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f'WS client connected. Total clients: {len(self.active_connections)}')

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f'WS client disconnected. Total clients: {len(self.active_connections)}')

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.error(f'Error broadcasting to client: {e}')
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

manager = ConnectionManager()
