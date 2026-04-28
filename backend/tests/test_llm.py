"""Tests for all LLM clients and factory."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.llm.base import BaseLLMClient, LLMResponse
from app.services.llm.ollama import OllamaClient
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.factory import create_llm_client


# ── LLMResponse ───────────────────────────────────────────────────────────────

class TestLLMResponse:
    def test_basic_creation(self):
        r = LLMResponse(content="hello", model="test")
        assert r.content == "hello"
        assert r.model == "test"
        assert r.input_tokens == 0
        assert r.output_tokens == 0
        assert r.reasoning is None

    def test_with_all_fields(self):
        r = LLMResponse(content="out", model="m", input_tokens=5, output_tokens=10, reasoning="thinking...")
        assert r.input_tokens == 5
        assert r.reasoning == "thinking..."


# ── BaseLLMClient ─────────────────────────────────────────────────────────────

class TestBaseLLMClient:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseLLMClient()

    async def test_complete_json_calls_complete_with_json_instruction(self):
        class ConcreteClient(BaseLLMClient):
            async def complete(self, prompt, system=None, temperature=0.2, max_tokens=8192):
                self.captured_system = system
                return LLMResponse(content='{"key": "val"}', model="m")
            async def stream(self, *a, **kw):
                yield ""

        client = ConcreteClient()
        result = await client.complete_json("test prompt", system="sys")
        assert "JSON" in client.captured_system
        assert result == '{"key": "val"}'

    async def test_complete_json_without_system(self):
        class ConcreteClient(BaseLLMClient):
            async def complete(self, prompt, system=None, temperature=0.2, max_tokens=8192):
                self.captured_system = system
                return LLMResponse(content='{}', model="m")
            async def stream(self, *a, **kw):
                yield ""

        client = ConcreteClient()
        await client.complete_json("test")
        assert "JSON" in client.captured_system


# ── OllamaClient ──────────────────────────────────────────────────────────────

def _mock_ollama_http(content: str, prompt_eval: int = 5, eval_count: int = 10):
    """Build a mock httpx context manager that returns an Ollama-style response."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": content},
        "prompt_eval_count": prompt_eval,
        "eval_count": eval_count,
    }
    mock_resp.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    return mock_ctx


class TestOllamaClient:
    def test_base_url_strips_trailing_slash(self):
        c = OllamaClient("http://localhost:11434/", "model")
        assert not c.base_url.endswith("/")

    async def test_complete_no_think_tags(self):
        with patch("httpx.AsyncClient", return_value=_mock_ollama_http("result text")):
            client = OllamaClient("http://localhost:11434", "deepseek-r1")
            result = await client.complete("prompt")

        assert result.content == "result text"
        assert result.reasoning is None
        assert result.input_tokens == 5
        assert result.output_tokens == 10
        assert result.model == "deepseek-r1"

    async def test_complete_with_think_tags(self):
        content = "<think>my reasoning here</think>final answer"
        with patch("httpx.AsyncClient", return_value=_mock_ollama_http(content)):
            client = OllamaClient("http://localhost:11434", "deepseek-r1")
            result = await client.complete("prompt")

        assert result.content == "final answer"
        assert result.reasoning == "my reasoning here"

    async def test_complete_with_system(self):
        with patch("httpx.AsyncClient", return_value=_mock_ollama_http("ok")) as MockClient:
            client = OllamaClient("http://localhost:11434", "model")
            await client.complete("prompt", system="be concise")
        # Verify system message was included
        call_kwargs = MockClient.return_value.__aenter__.return_value.post.call_args
        messages = call_kwargs[1]["json"]["messages"]
        roles = [m["role"] for m in messages]
        assert "system" in roles

    async def test_complete_without_system(self):
        with patch("httpx.AsyncClient", return_value=_mock_ollama_http("ok")) as MockClient:
            client = OllamaClient("http://localhost:11434", "model")
            await client.complete("prompt")
        call_kwargs = MockClient.return_value.__aenter__.return_value.post.call_args
        messages = call_kwargs[1]["json"]["messages"]
        roles = [m["role"] for m in messages]
        assert "system" not in roles

    async def test_stream_yields_chunks(self):
        lines = [
            '{"message": {"content": "hello"}, "done": false}',
            '{"message": {"content": " world"}, "done": false}',
            '{"message": {"content": ""}, "done": true}',
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_resp = MagicMock()
        mock_resp.aiter_lines = mock_aiter_lines

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_http = MagicMock()
        mock_http.stream = MagicMock(return_value=mock_stream_ctx)

        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx):
            client = OllamaClient("http://localhost:11434", "model")
            chunks = []
            async for chunk in client.stream("prompt"):
                chunks.append(chunk)

        assert chunks == ["hello", " world"]

    async def test_stream_skips_empty_lines(self):
        lines = ["", '{"message": {"content": "data"}, "done": false}']

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_resp = MagicMock()
        mock_resp.aiter_lines = mock_aiter_lines
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_http = MagicMock()
        mock_http.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx):
            client = OllamaClient("http://localhost:11434", "model")
            chunks = [c async for c in client.stream("p")]

        assert chunks == ["data"]


# ── OpenAIClient ──────────────────────────────────────────────────────────────

class TestOpenAIClient:
    def _make_openai_mock(self, content="reply", prompt_tokens=5, completion_tokens=10):
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = prompt_tokens
        mock_usage.completion_tokens = completion_tokens

        mock_choice = MagicMock()
        mock_choice.message.content = content

        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = mock_usage
        return mock_resp

    async def test_complete_with_usage(self):
        mock_resp = self._make_openai_mock("hello")
        mock_async_openai = MagicMock()
        mock_async_openai.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("openai.AsyncOpenAI", return_value=mock_async_openai):
            client = OpenAIClient("sk-test", "gpt-4o")
            result = await client.complete("prompt")

        assert result.content == "hello"
        assert result.input_tokens == 5
        assert result.output_tokens == 10

    async def test_complete_without_usage(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "answer"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = None

        mock_async_openai = MagicMock()
        mock_async_openai.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("openai.AsyncOpenAI", return_value=mock_async_openai):
            client = OpenAIClient("sk-test", "gpt-4o")
            result = await client.complete("prompt")

        assert result.input_tokens == 0
        assert result.output_tokens == 0

    async def test_complete_with_system(self):
        mock_resp = self._make_openai_mock()
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            client = OpenAIClient("sk-test", "gpt-4o")
            await client.complete("prompt", system="be brief")

        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert any(m["role"] == "system" for m in messages)

    async def test_complete_without_system(self):
        mock_resp = self._make_openai_mock()
        mock_openai = MagicMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            client = OpenAIClient("sk-test", "gpt-4o")
            await client.complete("prompt")

        messages = mock_openai.chat.completions.create.call_args[1]["messages"]
        assert all(m["role"] != "system" for m in messages)

    async def test_stream_yields_chunks(self):
        async def mock_chunk_iter():
            for text in ["tok1", "tok2", ""]:
                chunk = MagicMock()
                chunk.choices[0].delta.content = text
                yield chunk

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_chunk_iter())
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_openai = MagicMock()
        mock_openai.chat.completions.create = MagicMock(return_value=mock_stream_ctx)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            client = OpenAIClient("sk-test", "gpt-4o")
            chunks = [c async for c in client.stream("prompt")]

        assert chunks == ["tok1", "tok2"]


# ── AnthropicClient ───────────────────────────────────────────────────────────

class TestAnthropicClient:
    def _make_anthropic_mock(self, content_text="answer"):
        mock_block = MagicMock()
        mock_block.text = content_text

        mock_usage = MagicMock()
        mock_usage.input_tokens = 8
        mock_usage.output_tokens = 12

        mock_resp = MagicMock()
        mock_resp.content = [mock_block]
        mock_resp.usage = mock_usage
        return mock_resp

    async def test_complete_with_system(self):
        mock_resp = self._make_anthropic_mock("ans")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(return_value=mock_resp)

        with patch("anthropic.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient("sk-ant-test", "claude-3")
            result = await client.complete("prompt", system="be expert")

        assert result.content == "ans"
        assert result.input_tokens == 8
        assert result.output_tokens == 12
        call_kwargs = mock_anthropic.messages.create.call_args[1]
        assert "system" in call_kwargs

    async def test_complete_without_system(self):
        mock_resp = self._make_anthropic_mock()
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(return_value=mock_resp)

        with patch("anthropic.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient("sk-ant-test", "claude-3")
            await client.complete("prompt")

        call_kwargs = mock_anthropic.messages.create.call_args[1]
        assert "system" not in call_kwargs

    async def test_complete_handles_multiple_blocks(self):
        b1 = MagicMock(); b1.text = "part1"
        b2 = MagicMock(); b2.text = "part2"
        b3 = MagicMock(); del b3.text  # block without text attr

        mock_resp = MagicMock()
        mock_resp.content = [b1, b2, b3]
        mock_resp.usage = MagicMock(input_tokens=0, output_tokens=0)

        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(return_value=mock_resp)

        with patch("anthropic.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient("sk-ant", "claude-3")
            result = await client.complete("p")

        assert result.content == "part1part2"

    async def test_stream(self):
        async def mock_text_stream():
            yield "chunk1"
            yield "chunk2"

        mock_stream = MagicMock()
        mock_stream.text_stream = mock_text_stream()
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_anthropic = MagicMock()
        mock_anthropic.messages.stream = MagicMock(return_value=mock_stream_ctx)

        with patch("anthropic.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient("sk-ant", "claude-3")
            chunks = [c async for c in client.stream("prompt")]

        assert chunks == ["chunk1", "chunk2"]


# ── GeminiClient ──────────────────────────────────────────────────────────────

class TestGeminiClient:
    def _make_genai_mock(self, text="gemini answer", has_usage=True):
        mock_resp = MagicMock()
        mock_resp.text = text
        if has_usage:
            mock_resp.usage_metadata = MagicMock(
                prompt_token_count=7, candidates_token_count=14
            )
        else:
            mock_resp.usage_metadata = None
        return mock_resp

    async def test_complete_with_usage(self):
        mock_resp = self._make_genai_mock("hello gemini")
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_model.generate_content = MagicMock(return_value=mock_resp)
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
        mock_genai.GenerationConfig = MagicMock()

        with patch("google.generativeai", mock_genai, create=True):
            with patch("app.services.llm.gemini_client.GeminiClient.__init__") as mock_init:
                mock_init.return_value = None
                client = GeminiClient.__new__(GeminiClient)
                client._genai = mock_genai
                client.model = "gemini-flash"

                with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_resp)):
                    result = await client.complete("prompt")

        assert result.content == "hello gemini"

    async def test_complete_without_usage(self):
        mock_resp = self._make_genai_mock(has_usage=False)
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_model.generate_content = MagicMock(return_value=mock_resp)
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
        mock_genai.GenerationConfig = MagicMock()

        with patch("app.services.llm.gemini_client.GeminiClient.__init__", return_value=None):
            client = GeminiClient.__new__(GeminiClient)
            client._genai = mock_genai
            client.model = "gemini"

            with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_resp)):
                result = await client.complete("prompt")

        assert result.input_tokens == 0
        assert result.output_tokens == 0

    async def test_stream_yields_chunks(self):
        chunks_data = [MagicMock(text="a"), MagicMock(text="b"), MagicMock(text="")]
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
        mock_genai.GenerationConfig = MagicMock()

        with patch("app.services.llm.gemini_client.GeminiClient.__init__", return_value=None):
            client = GeminiClient.__new__(GeminiClient)
            client._genai = mock_genai
            client.model = "gemini"

            with patch("asyncio.to_thread", new=AsyncMock(return_value=iter(chunks_data))):
                result_chunks = [c async for c in client.stream("prompt")]

        assert result_chunks == ["a", "b"]


# ── Factory ───────────────────────────────────────────────────────────────────

class TestFactory:
    def test_creates_ollama_client(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.factory.settings.llm_provider", "ollama")
        monkeypatch.setattr("app.services.llm.factory.settings.ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr("app.services.llm.factory.settings.ollama_model", "deepseek-r1")
        client = create_llm_client()
        assert isinstance(client, OllamaClient)

    def test_creates_openai_client(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.factory.settings.llm_provider", "openai")
        monkeypatch.setattr("app.services.llm.factory.settings.openai_api_key", "sk-x")
        monkeypatch.setattr("app.services.llm.factory.settings.openai_model", "gpt-4o")
        with patch("openai.AsyncOpenAI"):
            client = create_llm_client()
        assert isinstance(client, OpenAIClient)

    def test_creates_anthropic_client(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.factory.settings.llm_provider", "anthropic")
        monkeypatch.setattr("app.services.llm.factory.settings.anthropic_api_key", "sk-ant")
        monkeypatch.setattr("app.services.llm.factory.settings.anthropic_model", "claude-3")
        with patch("anthropic.AsyncAnthropic"):
            client = create_llm_client()
        assert isinstance(client, AnthropicClient)

    def test_creates_gemini_client(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.factory.settings.llm_provider", "gemini")
        monkeypatch.setattr("app.services.llm.factory.settings.gemini_api_key", "AIza")
        monkeypatch.setattr("app.services.llm.factory.settings.gemini_model", "gemini-flash")
        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            client = create_llm_client()
        assert isinstance(client, GeminiClient)

    def test_raises_for_unknown_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.factory.settings.llm_provider", "unknown_llm")
        with pytest.raises(ValueError, match="Provider não suportado"):
            create_llm_client()
