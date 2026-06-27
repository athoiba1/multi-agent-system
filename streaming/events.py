from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import uuid


class EventType(str, Enum):
    SYSTEM = "system"
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    PIPELINE_START = "pipeline_start"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_ERROR = "pipeline_error"
    AGENT_THINKING = "agent_thinking"
    AGENT_OUTPUT = "agent_output"
    BATCH_START = "batch_start"
    BATCH_COMPLETE = "batch_complete"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    step_id: Optional[str] = None
    task_id: Optional[str] = None


class EventQueue:
    def __init__(self):
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers: list[asyncio.Queue[Event]] = []

    async def publish(self, event: Event):
        await self._queue.put(event)
        for subscriber in self._subscribers:
            await subscriber.put(event)

    async def subscribe(self) -> asyncio.Queue[Event]:
        subscriber: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: asyncio.Queue[Event]):
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    async def get(self) -> Event:
        return await self._queue.get()

    def task_done(self):
        self._queue.task_done()
