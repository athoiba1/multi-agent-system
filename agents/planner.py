from agents.base import Agent
from llm.client import LLMClient
from llm.prompts import PLANNER_SYSTEM
from streaming.events import EventQueue
from typing import Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class PlannerAgent(Agent):
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        event_queue: Optional[EventQueue] = None,
        **kwargs,
    ):
        super().__init__(name="planner", event_queue=event_queue, **kwargs)
        self.llm = llm_client or LLMClient()

    async def execute(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        user_request = input_data.get("user_request", "")

        response = await self.llm.complete_json(
            system_prompt=PLANNER_SYSTEM,
            user_prompt=f"Decompose this request into steps:\n\n{user_request}",
        )

        try:
            steps = json.loads(response)
            if isinstance(steps, dict) and "steps" in steps:
                steps = steps["steps"]
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON, using fallback")
            steps = [
                {"name": "retrieve_info", "description": "Gather information", "agent_type": "retriever", "dependencies": []},
                {"name": "analyze_data", "description": "Analyze findings", "agent_type": "analyzer", "dependencies": ["retrieve_info"]},
                {"name": "generate_output", "description": "Create final output", "agent_type": "writer", "dependencies": ["analyze_data"]},
            ]

        return {"steps": steps, "original_request": user_request}
