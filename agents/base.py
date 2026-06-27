from abc import ABC, abstractmethod
from typing import Any, Optional
from models.task import Step, StepStatus
from models.results import StepResult, ResultStatus
from streaming.events import EventQueue, Event, EventType
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


class Agent(ABC):
    def __init__(
        self,
        name: str,
        event_queue: Optional[EventQueue] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.name = name
        self.event_queue = event_queue
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def _emit_event(self, event_type: EventType, data: dict[str, Any], step_id: Optional[str] = None, task_id: Optional[str] = None):
        if self.event_queue:
            event = Event(type=event_type, data=data, step_id=step_id, task_id=task_id)
            await self.event_queue.publish(event)

    async def run(self, step: Step, context: dict[str, Any]) -> StepResult:
        start_time = time.time()
        step.status = StepStatus.RUNNING

        await self._emit_event(
            EventType.STEP_START,
            {"step_name": step.name, "agent": self.name},
            step_id=step.id,
            task_id=context.get("task_id"),
        )

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    step.status = StepStatus.RETRYING
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    await self._emit_event(
                        EventType.AGENT_THINKING,
                        {"message": f"Retry {attempt}/{self.max_retries}, waiting {delay:.1f}s"},
                        step_id=step.id,
                        task_id=context.get("task_id"),
                    )
                    await asyncio.sleep(delay)

                await self._emit_event(
                    EventType.AGENT_THINKING,
                    {"message": f"Executing {self.name}..."},
                    step_id=step.id,
                    task_id=context.get("task_id"),
                )

                result = await self.execute(step.input_data, context)

                step.status = StepStatus.COMPLETED
                step.output_data = result
                step.completed_at = time.time()

                duration_ms = (time.time() - start_time) * 1000
                await self._emit_event(
                    EventType.STEP_COMPLETE,
                    {"step_name": step.name, "agent": self.name, "duration_ms": duration_ms},
                    step_id=step.id,
                    task_id=context.get("task_id"),
                )

                return StepResult(
                    step_id=step.id,
                    step_name=step.name,
                    status=ResultStatus.SUCCESS,
                    output_data=result,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Agent {self.name} failed (attempt {attempt + 1}): {e}")
                await self._emit_event(
                    EventType.AGENT_OUTPUT,
                    {"message": f"Error: {e}", "attempt": attempt + 1},
                    step_id=step.id,
                    task_id=context.get("task_id"),
                )

        step.status = StepStatus.FAILED
        step.error = last_error
        duration_ms = (time.time() - start_time) * 1000

        await self._emit_event(
            EventType.STEP_ERROR,
            {"step_name": step.name, "agent": self.name, "error": last_error},
            step_id=step.id,
            task_id=context.get("task_id"),
        )

        return StepResult(
            step_id=step.id,
            step_name=step.name,
            status=ResultStatus.FAILED,
            error=last_error,
            duration_ms=duration_ms,
        )

    @abstractmethod
    async def execute(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        pass
