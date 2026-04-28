from .base import BaseLLMClient
from app.config import settings


def create_llm_client() -> BaseLLMClient:
    provider = settings.llm_provider

    if provider == "ollama":
        from .ollama import OllamaClient
        return OllamaClient(settings.ollama_base_url, settings.ollama_model)

    if provider == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient(settings.openai_api_key, settings.openai_model)

    if provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(settings.anthropic_api_key, settings.anthropic_model)

    if provider == "gemini":
        from .gemini_client import GeminiClient
        return GeminiClient(settings.gemini_api_key, settings.gemini_model)

    raise ValueError(f"Provider não suportado: {provider}")
