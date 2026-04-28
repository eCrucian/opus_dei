from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning: Optional[str] = None  # for models with CoT (deepseek-r1, o1)


class BaseLLMClient(ABC):
    """Model-agnostic interface for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Single-turn completion."""

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        """Streaming completion — yields text chunks."""

    async def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> str:
        """Completion expected to return valid JSON."""
        json_system = (system or "") + (
            "\n\nResposta DEVE ser JSON válido, sem markdown, sem explicações fora do JSON."
        )
        resp = await self.complete(prompt, json_system.strip(), temperature, max_tokens)
        return resp.content
