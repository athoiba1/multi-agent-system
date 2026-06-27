from fastapi import WebSocket
from streaming.events import EventQueue, Event
import asyncio
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_event(self, client_id: str, event: Event):
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_json({
                    "type": event.type.value,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                })
            except Exception as e:
                logger.error(f"Failed to send to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, event: Event):
        disconnected = []
        for client_id, ws in self.connections.items():
            try:
                await ws.send_json({
                    "type": event.type.value,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                })
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)


class SSEHandler:
    def __init__(self, event_queue: EventQueue):
        self.event_queue = event_queue

    async def event_stream(self, task_id: str = None):
        subscriber = await self.event_queue.subscribe()

        try:
            while True:
                try:
                    event = await asyncio.wait_for(subscriber.get(), timeout=1.0)
                    if task_id and event.task_id != task_id:
                        continue
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    continue
        finally:
            self.event_queue.unsubscribe(subscriber)
