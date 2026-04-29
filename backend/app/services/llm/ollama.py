import httpx
import json
from typing import AsyncIterator, Optional
from .base import BaseLLMClient, LLMResponse


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=1800.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["message"]["content"]
        reasoning = None
        # deepseek-r1 encloses CoT in <think>...</think>
        if "<think>" in content and "</think>" in content:
            start = content.index("<think>") + len("<think>")
            end = content.index("</think>")
            reasoning = content[start:end].strip()
            content = content[end + len("</think>"):].strip()

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            reasoning=reasoning,
        )

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=1800.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
