from agents.base import Agent
from llm.client import LLMClient
from llm.prompts import WRITER_SYSTEM
from streaming.events import EventQueue, EventType
from typing import Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class WriterAgent(Agent):
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        event_queue: Optional[EventQueue] = None,
        **kwargs,
    ):
        super().__init__(name="writer", event_queue=event_queue, **kwargs)
        self.llm = llm_client or LLMClient()

    async def execute(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        analysis_data = input_data.get("data", input_data)
        step_id = context.get("step_id")

        await self._emit_event(
            EventType.AGENT_OUTPUT,
            {"message": "Generating report..."},
            step_id=step_id,
            task_id=context.get("task_id"),
        )

        response = await self.llm.complete_json(
            system_prompt=WRITER_SYSTEM,
            user_prompt=f"Write a report based on this analysis:\n\n{json.dumps(analysis_data, indent=2)}",
        )

        try:
            report = json.loads(response)
        except json.JSONDecodeError:
            report = {
                "title": "Generated Report",
                "executive_summary": response[:500],
                "sections": [{"heading": "Analysis", "content": response}],
                "conclusions": ["Analysis completed"],
                "recommendations": [],
            }

        return report
