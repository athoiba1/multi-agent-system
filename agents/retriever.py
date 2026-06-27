from agents.base import Agent
from llm.client import LLMClient
from llm.prompts import RETRIEVER_SYSTEM
from streaming.events import EventQueue, EventType
from typing import Any, Optional
import json
import asyncio
import random
import logging

logger = logging.getLogger(__name__)


class RetrieverAgent(Agent):
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        event_queue: Optional[EventQueue] = None,
        simulate_failure: bool = False,
        **kwargs,
    ):
        super().__init__(name="retriever", event_queue=event_queue, **kwargs)
        self.llm = llm_client or LLMClient()
        self.simulate_failure = simulate_failure

    async def execute(self, input_data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", input_data.get("user_request", ""))
        step_id = context.get("step_id")

        await self._emit_event(
            EventType.AGENT_OUTPUT,
            {"message": f"Searching for: {query}"},
            step_id=step_id,
            task_id=context.get("task_id"),
        )

        if self.simulate_failure:
            await asyncio.sleep(0.5)
            raise Exception("Simulated API timeout - rate limit exceeded")

        await self._emit_event(
            EventType.AGENT_OUTPUT,
            {"message": "Fetching from multiple sources..."},
            step_id=step_id,
            task_id=context.get("task_id"),
        )

        await asyncio.sleep(0.3)

        response = await self.llm.complete_json(
            system_prompt=RETRIEVER_SYSTEM,
            user_prompt=f"Retrieve information about: {query}\n\nContext: {json.dumps(context.get('prior_results', {}))}",
        )

        try:
            results = json.loads(response)
        except json.JSONDecodeError:
            results = {
                "sources": [{"title": "Simulated Source", "findings": response}],
                "summary": response[:200],
                "key_facts": [response[:100]],
                "confidence": "medium",
            }

        return results
