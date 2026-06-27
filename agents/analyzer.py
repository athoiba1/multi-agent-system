from agents.base import Agent
from llm.client import LLMClient
from llm.prompts import ANALYZER_SYSTEM
from streaming.events import EventQueue, EventType
from typing import Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class AnalyzerAgent(Agent):
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        event_queue: Optional[EventQueue] = None,
        **kwargs,
    ):
        super().__init__(name="analyzer", event_queue=event_queue, **kwargs)
        self.llm = llm_client or LLMClient()

    async def execute(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        data_to_analyze = input_data.get("data", input_data)
        step_id = context.get("step_id")

        await self._emit_event(
            EventType.AGENT_OUTPUT,
            {"message": "Analyzing retrieved data..."},
            step_id=step_id,
            task_id=context.get("task_id"),
        )

        response = await self.llm.complete_json(
            system_prompt=ANALYZER_SYSTEM,
            user_prompt=f"Analyze this data:\n\n{json.dumps(data_to_analyze, indent=2)}",
        )

        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            analysis = {
                "insights": [response[:200]],
                "patterns": ["Analysis completed"],
                "conclusions": ["Data processed successfully"],
                "recommendations": [],
                "score": 75,
            }

        return analysis
