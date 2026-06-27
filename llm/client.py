import ollama
from typing import Optional
import logging
import os
import json

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        model: str = None,
        host: Optional[str] = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = ollama.AsyncClient(host=self.host)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response.message.content or ""

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        json_system = system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."
        response = await self.complete(
            system_prompt=json_system,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return cleaned
