from __future__ import annotations

import asyncio
import importlib
from typing import Any

import httpx
import ollama as ollama_sdk
import pytest

from promptkit.engines.anthropic import AnthropicEngine
from promptkit.engines.base import BaseEngine
from promptkit.engines.ollama import OllamaEngine
from promptkit.engines.openai import OpenAIEngine
from promptkit.errors import ProviderError
from promptkit.retry import NO_RETRY
from promptkit.types import Chunk


def http_stack(sdk: str) -> Any:
    base = importlib.import_module(f"{sdk}._base_client")

    for name in ("httpx2", "httpx"):
        module = getattr(base, name, None)

        if module is not None:
            return module

    raise RuntimeError(f"cannot determine the http stack used by {sdk}")


OPENAI_HTTP = http_stack("openai")
ANTHROPIC_HTTP = http_stack("anthropic")

OPENAI_SSE = (
    'data: {"choices":[{"delta":{"content":"Hel"},"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":null}]}\n\n'
    'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
    "data: [DONE]\n\n"
)

ANTHROPIC_SSE = (
    "event: content_block_delta\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":"Hel"}}\n\n'
    "event: content_block_delta\n"
    'data: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":"lo"}}\n\n'
    "event: message_delta\n"
    'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},'
    '"usage":{"output_tokens":2}}\n\n'
)

OLLAMA_NDJSON = (
    '{"model":"llama3","message":{"role":"assistant","content":"Hel"},"done":false}\n'
    '{"model":"llama3","message":{"role":"assistant","content":"lo"},"done":false}\n'
    '{"model":"llama3","message":{"role":"assistant","content":""},'
    '"done":true,"done_reason":"stop"}\n'
)


def sse_client(http: Any, body: str) -> Any:
    def handler(request: Any) -> Any:
        return http.Response(
            200, text=body, headers={"content-type": "text/event-stream"}
        )

    return http.Client(transport=http.MockTransport(handler))


class TestOpenAIStreaming:
    def test_chunks_join_into_the_full_text(self) -> None:
        with OpenAIEngine(
            api_key="k", http_client=sse_client(OPENAI_HTTP, OPENAI_SSE)
        ) as engine:
            chunks = list(engine.stream("hi"))

        assert "".join(c.text for c in chunks) == "Hello"
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_final_chunk_carries_the_finish_reason(self) -> None:
        with OpenAIEngine(
            api_key="k", http_client=sse_client(OPENAI_HTTP, OPENAI_SSE)
        ) as engine:
            chunks = list(engine.stream("hi"))

        assert chunks[-1].finish_reason == "stop"

    def test_errors_are_mapped_during_streaming(self) -> None:
        def handler(request: Any) -> Any:
            return OPENAI_HTTP.Response(401, json={"error": {"message": "nope"}})

        client = OPENAI_HTTP.Client(transport=OPENAI_HTTP.MockTransport(handler))

        from promptkit.errors import AuthenticationError

        with (
            OpenAIEngine(api_key="k", retry=NO_RETRY, http_client=client) as engine,
            pytest.raises(AuthenticationError),
        ):
            list(engine.stream("hi"))


class TestAnthropicStreaming:
    def test_chunks_join_into_the_full_text(self) -> None:
        with AnthropicEngine(
            api_key="k", http_client=sse_client(ANTHROPIC_HTTP, ANTHROPIC_SSE)
        ) as engine:
            chunks = list(engine.stream("hi"))

        assert "".join(c.text for c in chunks) == "Hello"

    def test_stop_reason_is_surfaced(self) -> None:
        with AnthropicEngine(
            api_key="k", http_client=sse_client(ANTHROPIC_HTTP, ANTHROPIC_SSE)
        ) as engine:
            reasons = [c.finish_reason for c in engine.stream("hi") if c.finish_reason]

        assert reasons == ["end_turn"]

    def test_system_prompt_is_hoisted_when_streaming(self) -> None:
        import json

        seen: dict[str, Any] = {}

        def handler(request: Any) -> Any:
            seen["body"] = json.loads(request.content)

            return ANTHROPIC_HTTP.Response(
                200, text=ANTHROPIC_SSE, headers={"content-type": "text/event-stream"}
            )

        client = ANTHROPIC_HTTP.Client(transport=ANTHROPIC_HTTP.MockTransport(handler))

        from promptkit.types import Message

        with AnthropicEngine(api_key="k", http_client=client) as engine:
            list(engine.stream([Message("system", "Be brief."), Message("user", "hi")]))

        assert seen["body"]["system"] == "Be brief."
        assert seen["body"]["stream"] is True


class TestOllamaStreaming:
    def _engine(self, body: str) -> OllamaEngine:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, text=body, headers={"content-type": "application/x-ndjson"}
            )

        engine = OllamaEngine()
        engine._client = ollama_sdk.Client(
            host=engine.host, transport=httpx.MockTransport(handler)
        )

        return engine

    def test_chunks_join_into_the_full_text(self) -> None:
        engine = self._engine(OLLAMA_NDJSON)
        chunks = list(engine.stream("hi"))
        engine.close()

        assert "".join(c.text for c in chunks) == "Hello"

    def test_done_reason_is_surfaced(self) -> None:
        engine = self._engine(OLLAMA_NDJSON)
        reasons = [c.finish_reason for c in engine.stream("hi") if c.finish_reason]
        engine.close()

        assert reasons == ["stop"]


class TestAsyncStreaming:
    def test_openai_astream(self) -> None:
        async def go() -> list[str]:
            def handler(request: Any) -> Any:
                return OPENAI_HTTP.Response(
                    200,
                    text=OPENAI_SSE,
                    headers={"content-type": "text/event-stream"},
                )

            client = OPENAI_HTTP.AsyncClient(
                transport=OPENAI_HTTP.MockTransport(handler)
            )
            engine = OpenAIEngine(api_key="k", http_client=client)
            try:
                return [chunk.text async for chunk in engine.astream("hi")]
            finally:
                await engine.aclose()

        assert "".join(asyncio.run(go())) == "Hello"

    def test_anthropic_astream(self) -> None:
        async def go() -> list[str]:
            def handler(request: Any) -> Any:
                return ANTHROPIC_HTTP.Response(
                    200,
                    text=ANTHROPIC_SSE,
                    headers={"content-type": "text/event-stream"},
                )

            client = ANTHROPIC_HTTP.AsyncClient(
                transport=ANTHROPIC_HTTP.MockTransport(handler)
            )
            engine = AnthropicEngine(api_key="k", http_client=client)
            try:
                return [chunk.text async for chunk in engine.astream("hi")]
            finally:
                await engine.aclose()

        assert "".join(asyncio.run(go())) == "Hello"


class TestCapabilityHonesty:
    @pytest.mark.parametrize(
        "engine_class", [OpenAIEngine, AnthropicEngine, OllamaEngine]
    )
    def test_engines_that_claim_streaming_implement_it(
        self, engine_class: type[BaseEngine]
    ) -> None:
        assert engine_class.capabilities.streaming is True
        assert "stream" in vars(engine_class)
        assert "astream" in vars(engine_class)

    def test_an_engine_without_streaming_raises(self) -> None:
        from promptkit.types import Completion, Message

        class Plain(BaseEngine):
            def _complete(self, messages: list[Message], **options: Any) -> Completion:
                return Completion(text="", model=self.model)

        with pytest.raises(NotImplementedError, match="streaming"):
            Plain("m").stream("hi")


class TestConnectionFailures:
    def test_ollama_unreachable_is_actionable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        engine = OllamaEngine(retry=NO_RETRY)
        engine._client = ollama_sdk.Client(
            host=engine.host, transport=httpx.MockTransport(handler)
        )

        with pytest.raises(ProviderError):
            engine.complete("hi")

        engine.close()
