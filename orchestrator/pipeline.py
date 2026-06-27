from typing import Any, Optional
from models.task import Task, Step, StepStatus
from models.results import PipelineResult, StepResult, ResultStatus
from agents.base import Agent
from streaming.events import EventQueue, EventType
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        agents: dict[str, Agent],
        event_queue: Optional[EventQueue] = None,
    ):
        self.agents = agents
        self.event_queue = event_queue

    async def _emit_event(self, event_type: EventType, data: dict[str, Any], task_id: Optional[str] = None):
        if self.event_queue:
            event = Event(type=event_type, data=data, task_id=task_id)
            await self.event_queue.publish(event)

    def _get_ready_steps(self, task: Task) -> list[Step]:
        ready = []
        for step in task.steps:
            if step.status != StepStatus.PENDING:
                continue
            deps_met = all(
                any(s.name == dep and s.status == StepStatus.COMPLETED for s in task.steps)
                for dep in step.dependencies
            )
            if deps_met:
                ready.append(step)
        return ready

    def _build_dependency_graph(self, task: Task) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        for step in task.steps:
            graph[step.name] = step.dependencies
        return graph

    def _topological_sort(self, task: Task) -> list[Step]:
        graph = self._build_dependency_graph(task)
        visited: set[str] = set()
        order: list[str] = []

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                dfs(dep)
            order.append(node)

        for step_name in graph:
            dfs(step_name)

        step_map = {s.name: s for s in task.steps}
        return [step_map[name] for name in order if name in step_map]

    async def execute(self, task: Task) -> PipelineResult:
        start_time = time.time()

        await self._emit_event(
            EventType.PIPELINE_START,
            {"task_id": task.id, "steps_count": len(task.steps)},
            task_id=task.id,
        )

        ordered_steps = self._topological_sort(task)
        steps_results: list[StepResult] = []
        context: dict[str, Any] = {"task_id": task.id, "prior_results": {}}
        final_status = ResultStatus.SUCCESS

        for step in ordered_steps:
            agent = self.agents.get(step.agent_type)
            if not agent:
                result = StepResult(
                    step_id=step.id,
                    step_name=step.name,
                    status=ResultStatus.FAILED,
                    error=f"Unknown agent type: {step.agent_type}",
                )
                steps_results.append(result)
                final_status = ResultStatus.FAILED
                continue

            step.input_data = {**step.input_data, **context.get("prior_results", {})}
            context["step_id"] = step.id

            result = await agent.run(step, context)
            steps_results.append(result)

            if result.status == ResultStatus.SUCCESS:
                context["prior_results"][step.name] = result.output_data
            else:
                final_status = ResultStatus.PARTIAL

        total_duration = (time.time() - start_time) * 1000

        final_output = context["prior_results"].get(
            ordered_steps[-1].name if ordered_steps else "",
            {},
        )

        pipeline_result = PipelineResult(
            task_id=task.id,
            status=final_status,
            steps_results=steps_results,
            final_output=final_output,
            total_duration_ms=total_duration,
        )

        event_type = EventType.PIPELINE_COMPLETE if final_status != ResultStatus.FAILED else EventType.PIPELINE_ERROR
        await self._emit_event(
            event_type,
            {
                "task_id": task.id,
                "status": final_status.value,
                "duration_ms": total_duration,
                "steps_completed": sum(1 for r in steps_results if r.status == ResultStatus.SUCCESS),
                "steps_failed": sum(1 for r in steps_results if r.status == ResultStatus.FAILED),
            },
            task_id=task.id,
        )

        return pipeline_result
