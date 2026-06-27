from typing import Any, Optional
from models.task import Task, Step
from agents.planner import PlannerAgent
from streaming.events import EventQueue, EventType
import logging

logger = logging.getLogger(__name__)


class Decomposer:
    def __init__(
        self,
        planner_agent: Optional[PlannerAgent] = None,
        event_queue: Optional[EventQueue] = None,
    ):
        self.planner = planner_agent or PlannerAgent(event_queue=event_queue)
        self.event_queue = event_queue

    async def decompose(self, user_request: str) -> Task:
        task = Task(original_request=user_request)

        if self.event_queue:
            await self.event_queue.publish(
                Event(
                    type=EventType.AGENT_THINKING,
                    data={"message": "Analyzing request and creating execution plan..."},
                    task_id=task.id,
                )
            )

        result = await self.planner.execute(
            {"user_request": user_request},
            {"task_id": task.id},
        )

        steps_data = result.get("steps", [])
        for step_data in steps_data:
            step = Step(
                name=step_data.get("name", f"step_{len(task.steps)}"),
                description=step_data.get("description", ""),
                agent_type=step_data.get("agent_type", "retriever"),
                dependencies=step_data.get("dependencies", []),
                input_data={"user_request": user_request},
            )
            task.steps.append(step)

        if not task.steps:
            task.steps = [
                Step(
                    name="retrieve_info",
                    description="Gather information",
                    agent_type="retriever",
                    input_data={"user_request": user_request},
                ),
                Step(
                    name="analyze_data",
                    description="Analyze findings",
                    agent_type="analyzer",
                    dependencies=["retrieve_info"],
                ),
                Step(
                    name="generate_output",
                    description="Create final output",
                    agent_type="writer",
                    dependencies=["analyze_data"],
                ),
            ]

        return task
