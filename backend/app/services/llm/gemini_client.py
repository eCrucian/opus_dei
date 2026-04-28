from typing import AsyncIterator, Optional
from .base import BaseLLMClient, LLMResponse


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self.model = model

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        import asyncio
        model = self._genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(
                temperature=temperature, max_output_tokens=max_tokens
            ),
        )
        resp = await asyncio.to_thread(model.generate_content, prompt)
        return LLMResponse(
            content=resp.text,
            model=self.model,
            input_tokens=resp.usage_metadata.prompt_token_count if resp.usage_metadata else 0,
            output_tokens=resp.usage_metadata.candidates_token_count if resp.usage_metadata else 0,
        )

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> AsyncIterator[str]:
        import asyncio
        model = self._genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(
                temperature=temperature, max_output_tokens=max_tokens
            ),
        )
        resp = await asyncio.to_thread(
            model.generate_content, prompt, stream=True
        )
        for chunk in resp:
            if chunk.text:
                yield chunk.text
