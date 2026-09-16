from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace
from typing import Any, ClassVar

import httpx
import ollama as ollama_sdk
import pytest

from promptkit.engines import anthropic as anthropic_engine
from promptkit.engines import ollama as ollama_engine
from promptkit.engines import openai as openai_engine
from promptkit.engines import plugins
from promptkit.engines.anthropic import AnthropicEngine, split_system
from promptkit.engines.anthropic import map_error as anthropic_error
from promptkit.engines.anthropic import (
    parse_response as anthropic_parse,
)
from promptkit.engines.base import BaseEngine
from promptkit.engines.compatible import KNOWN_ENDPOINTS, CompatibleEngine
from promptkit.engines.ollama import OllamaEngine
from promptkit.engines.openai import OpenAIEngine
from promptkit.engines.openai import map_error as openai_error
from promptkit.engines.openai import parse_chunk as openai_chunk
from promptkit.engines.openai import parse_response as openai_parse
from promptkit.errors import (
    AuthenticationError,
    EngineNotFoundError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from promptkit.retry import NO_RETRY, RetryPolicy
from promptkit.types import Capabilities, Completion, Message, Usage

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_URL = "http://localhost:11434/api/chat"


def http_stack(sdk: str) -> Any:
    base = importlib.import_module(f"{sdk}._base_client")

    for name in ("httpx2", "httpx"):
        module = getattr(base, name, None)

        if module is not None:
            return module

    raise RuntimeError(f"cannot determine the http stack used by {sdk}")


OPENAI_HTTP = http_stack("openai")
ANTHROPIC_HTTP = http_stack("anthropic")


def mock_client(handler: Any, http: Any = OPENAI_HTTP) -> Any:
    return http.Client(transport=http.MockTransport(handler))


def mock_async_client(handler: Any, http: Any = OPENAI_HTTP) -> Any:
    return http.AsyncClient(transport=http.MockTransport(handler))


def openai_payload(text: str = "pong", **usage: int) -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 3),
            "completion_tokens": usage.get("completion_tokens", 1),
            "total_tokens": 4,
        },
    }


class Recording(BaseEngine):
    def __init__(self, results: list[Any], model: str = "test", **kw: Any) -> None:
        super().__init__(model, **kw)
        self.results = results
        self.attempts = 0

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        self.attempts += 1
        result = self.results.pop(0)

        if isinstance(result, Exception):
            raise result

        return Completion(text=result, model=self.model, usage=Usage(1, 1))


class TestPlugins:
    def test_builtin_engines_are_discoverable(self) -> None:
        assert set(plugins.names()) == {
            "openai",
            "anthropic",
            "ollama",
            "compatible",
        }

    def test_discover_reports_installed_state(self) -> None:
        info = plugins.discover()["openai"]

        assert info.installed is True
        assert info.hint is None
        assert info.target.endswith("OpenAIEngine")

    def test_load_returns_the_class(self) -> None:
        assert plugins.load("anthropic") is AnthropicEngine

    def test_unknown_engine_lists_the_known_ones(self) -> None:
        with pytest.raises(EngineNotFoundError) as exc:
            plugins.load("not-a-real-engine")

        assert "openai" in str(exc.value)

    def test_missing_extra_names_the_install_command(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(plugins, "is_available", lambda module: False)

        with pytest.raises(EngineNotFoundError) as exc:
            plugins.load("openai")

        assert "promptkit-core[openai]" in str(exc.value)

    def test_info_hint_for_uninstalled_extra(self) -> None:
        info = plugins.EngineInfo("x", "t", "openai", installed=False)

        assert info.hint == "pip install 'promptkit-core[openai]'"


class TestOpenAIPure:
    def test_roles_are_preserved(self) -> None:
        params = openai_engine.build_params(
            [Message("system", "S"), Message("user", "U")], "gpt-4o", 0.5
        )

        assert params["messages"] == [
            {"role": "system", "content": "S"},
            {"role": "user", "content": "U"},
        ]

    def test_optional_params_omitted(self) -> None:
        params = openai_engine.build_params([], "m", None, None)

        assert "temperature" not in params
        assert "max_tokens" not in params

    def test_json_schema_becomes_response_format(self) -> None:
        schema = {"type": "object", "properties": {}}
        params = openai_engine.build_params([], "m", None, None, schema)

        assert params["response_format"]["type"] == "json_schema"
        assert params["response_format"]["json_schema"]["schema"] == schema

    def test_extra_options_pass_through(self) -> None:
        params = openai_engine.build_params(
            [], "m", None, None, None, seed=7, top_p=None
        )

        assert params["seed"] == 7
        assert "top_p" not in params

    def test_usage_is_read_from_the_response(self) -> None:
        raw = SimpleNamespace(
            model="gpt-4o",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="hi"), finish_reason="stop"
                )
            ],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=4),
        )
        completion = openai_parse(raw, "gpt-4o")

        assert completion.usage == Usage(11, 4, estimated=False)
        assert completion.finish_reason == "stop"
        assert completion.raw is raw

    def test_missing_usage_is_estimated(self) -> None:
        raw = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))], usage=None
        )

        assert openai_parse(raw, "m").usage.estimated is True

    def test_no_choices_raises(self) -> None:
        with pytest.raises(ProviderError, match="No choices"):
            openai_parse(SimpleNamespace(choices=[]), "m")

    def test_null_content_raises(self) -> None:
        raw = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
        )

        with pytest.raises(ProviderError, match="No content"):
            openai_parse(raw, "m")

    def test_chunk_parsing(self) -> None:
        raw = SimpleNamespace(
            choices=[
                SimpleNamespace(delta=SimpleNamespace(content="a"), finish_reason=None)
            ]
        )
        chunk = openai_chunk(raw)

        assert chunk is not None
        assert chunk.text == "a"

    def test_empty_chunk_is_skipped(self) -> None:
        raw = SimpleNamespace(
            choices=[
                SimpleNamespace(delta=SimpleNamespace(content=None), finish_reason=None)
            ]
        )

        assert openai_chunk(raw) is None

    def test_chunk_without_choices_is_skipped(self) -> None:
        assert openai_chunk(SimpleNamespace(choices=[])) is None


class TestOpenAIErrorMapping:
    def _response(self, status: int, retry_after: str | None = None) -> Any:
        headers = {"retry-after": retry_after} if retry_after else {}

        return OPENAI_HTTP.Response(
            status, request=OPENAI_HTTP.Request("POST", OPENAI_URL), headers=headers
        )

    def test_authentication(self) -> None:
        import openai

        error = openai.AuthenticationError(
            "bad key", response=self._response(401), body=None
        )

        assert isinstance(openai_error(error, "m"), AuthenticationError)

    def test_rate_limit_carries_retry_after(self) -> None:
        import openai

        error = openai.RateLimitError(
            "slow down", response=self._response(429, "2.5"), body=None
        )
        mapped = openai_error(error, "m")

        assert isinstance(mapped, RateLimitError)
        assert mapped.retry_after == 2.5

    def test_not_found_is_model_not_found(self) -> None:
        import openai

        error = openai.NotFoundError(
            "no model", response=self._response(404), body=None
        )

        assert isinstance(openai_error(error, "m"), ModelNotFoundError)

    def test_connection_error_is_actionable(self) -> None:
        import openai

        error = openai.APIConnectionError(
            request=OPENAI_HTTP.Request("POST", OPENAI_URL)
        )
        mapped = openai_error(error, "m")

        assert isinstance(mapped, ProviderError)
        assert "reach" in str(mapped)

    def test_unrelated_exception_is_reraised(self) -> None:
        with pytest.raises(ZeroDivisionError):
            openai_error(ZeroDivisionError("boom"), "m")


class TestAnthropicPure:
    def test_system_is_hoisted_out_of_messages(self) -> None:
        system, rest = split_system(
            [Message("system", "S"), Message("user", "U"), Message("system", "S2")]
        )

        assert system == "S\n\nS2"
        assert [m.role for m in rest] == ["user"]

    def test_params_put_system_at_top_level(self) -> None:
        params = anthropic_engine.build_params(
            [Message("system", "Be brief."), Message("user", "Hi")],
            "claude-sonnet-4",
            0.2,
            100,
        )

        assert params["system"] == "Be brief."
        assert params["messages"] == [{"role": "user", "content": "Hi"}]
        assert params["max_tokens"] == 100

    def test_max_tokens_is_always_sent(self) -> None:
        params = anthropic_engine.build_params([Message("user", "x")], "m", None, None)

        assert params["max_tokens"] == anthropic_engine.DEFAULT_MAX_TOKENS

    def test_no_system_key_when_absent(self) -> None:
        params = anthropic_engine.build_params([Message("user", "x")], "m")

        assert "system" not in params

    def test_text_blocks_are_joined(self) -> None:
        raw = SimpleNamespace(
            model="claude-sonnet-4",
            content=[
                SimpleNamespace(type="text", text="Hello "),
                SimpleNamespace(type="text", text="world"),
            ],
            usage=SimpleNamespace(input_tokens=7, output_tokens=2),
            stop_reason="end_turn",
        )
        completion = anthropic_parse(raw, "claude-sonnet-4")

        assert completion.text == "Hello world"
        assert completion.usage == Usage(7, 2, estimated=False)
        assert completion.finish_reason == "end_turn"

    def test_non_text_blocks_are_ignored(self) -> None:
        raw = SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", text="secret"),
                SimpleNamespace(type="text", text="visible"),
            ],
            usage=None,
        )

        assert anthropic_parse(raw, "m").text == "visible"

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ProviderError, match="No text content"):
            anthropic_parse(SimpleNamespace(content=[], usage=None), "m")

    def test_stream_event_parsing(self) -> None:
        event = SimpleNamespace(
            type="content_block_delta", delta=SimpleNamespace(text="hi")
        )
        chunk = anthropic_engine.parse_event(event)

        assert chunk is not None
        assert chunk.text == "hi"

    def test_stop_reason_event(self) -> None:
        event = SimpleNamespace(
            type="message_delta", delta=SimpleNamespace(stop_reason="end_turn")
        )
        chunk = anthropic_engine.parse_event(event)

        assert chunk is not None
        assert chunk.finish_reason == "end_turn"

    def test_irrelevant_event_is_skipped(self) -> None:
        assert anthropic_engine.parse_event(SimpleNamespace(type="ping")) is None

    def test_rate_limit_mapping(self) -> None:
        import anthropic

        error = anthropic.RateLimitError(
            "slow",
            response=ANTHROPIC_HTTP.Response(
                429, request=ANTHROPIC_HTTP.Request("POST", ANTHROPIC_URL)
            ),
            body=None,
        )

        assert isinstance(anthropic_error(error, "m"), RateLimitError)

    def test_json_mode_not_advertised(self) -> None:
        assert AnthropicEngine.capabilities.json_mode is False


class TestOllamaPure:
    def test_params(self) -> None:
        params = ollama_engine.build_params([Message("user", "hi")], "llama3", 0.5, 64)

        assert params["options"] == {"temperature": 0.5, "num_predict": 64}
        assert params["messages"] == [{"role": "user", "content": "hi"}]

    def test_json_schema_becomes_format(self) -> None:
        schema = {"type": "object"}
        params = ollama_engine.build_params([], "m", None, None, schema)

        assert params["format"] == schema

    def test_dict_response_is_parsed(self) -> None:
        completion = ollama_engine.parse_response(
            {
                "model": "llama3",
                "message": {"content": "hi"},
                "prompt_eval_count": 12,
                "eval_count": 5,
                "done_reason": "stop",
            },
            "llama3",
        )

        assert completion.text == "hi"
        assert completion.usage == Usage(12, 5, estimated=False)

    def test_object_response_is_parsed(self) -> None:
        raw = SimpleNamespace(
            model="llama3",
            message=SimpleNamespace(content="hi"),
            prompt_eval_count=1,
            eval_count=1,
            done_reason=None,
        )

        assert ollama_engine.parse_response(raw, "llama3").text == "hi"

    def test_legacy_generate_shape(self) -> None:
        assert ollama_engine.parse_response({"response": "old"}, "m").text == "old"

    def test_missing_content_raises(self) -> None:
        with pytest.raises(ProviderError, match="No content"):
            ollama_engine.parse_response({}, "m")

    def test_chunk_parsing(self) -> None:
        chunk = ollama_engine.parse_chunk({"message": {"content": "a"}, "done": False})

        assert chunk is not None
        assert chunk.text == "a"

    def test_final_chunk_carries_done_reason(self) -> None:
        chunk = ollama_engine.parse_chunk(
            {"message": {"content": ""}, "done": True, "done_reason": "stop"}
        )

        assert chunk is not None
        assert chunk.finish_reason == "stop"

    def test_missing_model_gives_install_hint(self) -> None:
        import ollama

        error = ollama.ResponseError("model not found", status_code=404)
        mapped = ollama_engine.map_error(error, "ghost", "http://localhost:11434")

        assert isinstance(mapped, ModelNotFoundError)
        assert "ollama pull ghost" in str(mapped)

    def test_connection_error_is_actionable(self) -> None:
        mapped = ollama_engine.map_error(
            ConnectionError("refused"), "m", "http://localhost:11434"
        )

        assert "Is it running" in str(mapped)


class TestTransport:
    def test_openai_round_trip(self) -> None:
        seen: dict[str, Any] = {}

        def handler(request: Any) -> Any:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["body"] = json.loads(request.content)

            return OPENAI_HTTP.Response(200, json=openai_payload())

        with OpenAIEngine(
            api_key="sk-test", http_client=mock_client(handler)
        ) as engine:
            completion = engine.complete("ping")

        assert completion.text == "pong"
        assert completion.usage == Usage(3, 1, estimated=False)
        assert seen["url"] == OPENAI_URL
        assert seen["auth"] == "Bearer sk-test"
        assert seen["body"]["messages"] == [{"role": "user", "content": "ping"}]

    def test_openai_maps_status_errors(self) -> None:
        client = mock_client(
            lambda r: OPENAI_HTTP.Response(401, json={"error": {"message": "nope"}})
        )

        with (
            OpenAIEngine(api_key="k", retry=NO_RETRY, http_client=client) as engine,
            pytest.raises(AuthenticationError, match="nope"),
        ):
            engine.complete("ping")

    def test_openai_retries_then_succeeds(self) -> None:
        calls = {"n": 0}

        def handler(request: Any) -> Any:
            calls["n"] += 1

            if calls["n"] == 1:
                return OPENAI_HTTP.Response(429, json={"error": {"message": "slow"}})

            return OPENAI_HTTP.Response(200, json=openai_payload("recovered"))

        policy = RetryPolicy(attempts=2, initial_backoff=0.0, jitter=False)

        with OpenAIEngine(
            api_key="k", retry=policy, http_client=mock_client(handler)
        ) as engine:
            completion = engine.complete("ping")

        assert completion.text == "recovered"
        assert calls["n"] == 2

    def test_openai_async_round_trip(self) -> None:
        async def go() -> Completion:
            engine = OpenAIEngine(
                api_key="k",
                http_client=mock_async_client(
                    lambda r: OPENAI_HTTP.Response(
                        200, json=openai_payload("async-pong")
                    )
                ),
            )
            try:
                return await engine.acomplete("ping")
            finally:
                await engine.aclose()

        assert asyncio.run(go()).text == "async-pong"

    def test_compatible_engine_uses_its_base_url(self) -> None:
        seen: dict[str, Any] = {}

        def handler(request: Any) -> Any:
            seen["url"] = str(request.url)

            return OPENAI_HTTP.Response(200, json=openai_payload("groq"))

        with CompatibleEngine(
            base_url="groq", model="llama-3.1-8b", http_client=mock_client(handler)
        ) as engine:
            assert engine.complete("ping").text == "groq"

        assert seen["url"].startswith(KNOWN_ENDPOINTS["groq"])

    def test_anthropic_round_trip(self) -> None:
        seen: dict[str, Any] = {}

        def handler(request: Any) -> Any:
            seen["body"] = json.loads(request.content)

            return ANTHROPIC_HTTP.Response(
                200,
                json={
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-sonnet-4",
                    "content": [{"type": "text", "text": "hello"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                },
            )

        with AnthropicEngine(
            api_key="sk-ant", http_client=mock_client(handler, ANTHROPIC_HTTP)
        ) as engine:
            completion = engine.complete(
                [Message("system", "Be brief."), Message("user", "Hi")]
            )

        assert completion.text == "hello"
        assert completion.usage == Usage(5, 2, estimated=False)
        assert seen["body"]["system"] == "Be brief."
        assert seen["body"]["messages"] == [{"role": "user", "content": "Hi"}]

    def test_ollama_round_trip(self) -> None:
        seen: dict[str, Any] = {}

        def handler(request: Any) -> Any:
            seen["url"] = str(request.url)

            return httpx.Response(
                200,
                json={
                    "model": "llama3",
                    "message": {"role": "assistant", "content": "hi"},
                    "done": True,
                    "done_reason": "stop",
                    "prompt_eval_count": 4,
                    "eval_count": 2,
                },
            )

        engine = OllamaEngine()
        engine._client = ollama_sdk.Client(
            host=engine.host, transport=httpx.MockTransport(handler)
        )
        completion = engine.complete("ping")
        engine.close()

        assert completion.text == "hi"
        assert completion.usage == Usage(4, 2, estimated=False)
        assert seen["url"] == OLLAMA_URL


class TestRetry:
    def test_retries_rate_limit_then_succeeds(self) -> None:
        engine = Recording(
            [RateLimitError("slow", retry_after=0.0), "ok"],
            retry=RetryPolicy(attempts=3, initial_backoff=0.0, jitter=False),
        )

        assert engine.complete("hi").text == "ok"
        assert engine.attempts == 2

    def test_does_not_retry_non_retryable(self) -> None:
        engine = Recording(
            [AuthenticationError("bad key"), "ok"],
            retry=RetryPolicy(attempts=3, initial_backoff=0.0),
        )

        with pytest.raises(AuthenticationError):
            engine.complete("hi")

        assert engine.attempts == 1

    def test_no_retry_policy(self) -> None:
        engine = Recording([RateLimitError("a"), "ok"], retry=NO_RETRY)

        with pytest.raises(RateLimitError):
            engine.complete("hi")

    def test_backoff_is_bounded(self) -> None:
        policy = RetryPolicy(initial_backoff=1.0, max_backoff=4.0, jitter=False)

        assert [policy.backoff(i) for i in (1, 2, 3, 4)] == [1.0, 2.0, 4.0, 4.0]

    def test_retry_after_overrides_backoff(self) -> None:
        policy = RetryPolicy(initial_backoff=10.0, jitter=False)

        assert policy.backoff(1, retry_after=2.0) == 2.0

    def test_sdk_retries_are_disabled(self) -> None:
        with OpenAIEngine(api_key="k") as engine:
            assert engine.client.max_retries == 0


class TestEngineContract:
    def test_complete_is_required(self) -> None:
        broken = type("Broken", (BaseEngine,), {})

        with pytest.raises(TypeError, match="abstract"):
            broken("m")

    def test_generate_is_a_convenience_over_complete(self) -> None:
        assert Recording(["modern"]).generate("hi") == "modern"

    def test_generate_async_is_a_convenience_over_acomplete(self) -> None:
        assert asyncio.run(Recording(["modern"]).generate_async("hi")) == "modern"

    def test_acomplete_defaults_to_complete(self) -> None:
        assert asyncio.run(Recording(["sync-path"]).acomplete("hi")).text == "sync-path"

    def test_string_becomes_a_user_message(self) -> None:
        class Capture(BaseEngine):
            seen: ClassVar[list[Message]] = []

            def _complete(self, messages: list[Message], **options: Any) -> Completion:
                type(self).seen = messages

                return Completion(text="", model=self.model)

        Capture("m").complete("hello")

        assert Capture.seen == [Message(role="user", content="hello")]


class TestLifecycle:
    def test_client_is_lazy_and_reused(self) -> None:
        engine = OpenAIEngine(api_key="k")

        assert engine._client is None
        assert engine.client is engine.client
        engine.close()
        assert engine._client is None

    def test_sync_context_manager(self) -> None:
        with OpenAIEngine(api_key="k") as engine:
            assert engine.model == "gpt-4o-mini"

    def test_async_context_manager(self) -> None:
        async def go() -> str:
            async with AnthropicEngine(api_key="k") as engine:
                return engine.model

        assert asyncio.run(go()) == "claude-sonnet-4"

    def test_no_del_finalizer(self) -> None:
        for engine_class in (OpenAIEngine, AnthropicEngine, OllamaEngine):
            assert "__del__" not in vars(engine_class)

    def test_api_key_absent_from_model_info(self) -> None:
        with OpenAIEngine(api_key="sk-secret") as engine:
            assert "sk-secret" not in str(engine.get_model_info())

    def test_raw_response_is_exposed(self) -> None:
        raw = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="x"))], usage=None
        )

        assert openai_parse(raw, "m").raw is raw

    def test_underlying_sdk_client_is_reachable(self) -> None:
        with OpenAIEngine(api_key="k") as engine:
            assert hasattr(engine.client, "chat")


class TestCapabilities:
    def test_engines_declare_capabilities(self) -> None:
        assert isinstance(OpenAIEngine.capabilities, Capabilities)
        assert OpenAIEngine.capabilities.json_mode is True

    def test_compatible_does_not_claim_json_mode(self) -> None:
        assert CompatibleEngine.capabilities.json_mode is False

    def test_known_endpoint_aliases(self) -> None:
        with CompatibleEngine(base_url="together", model="m") as engine:
            assert engine.base_url == KNOWN_ENDPOINTS["together"]

    def test_arbitrary_base_url_passes_through(self) -> None:
        with CompatibleEngine(base_url="https://my.host/v1", model="m") as engine:
            assert engine.base_url == "https://my.host/v1"


class TestCost:
    def test_cost_uses_real_usage(self) -> None:
        engine = Recording(["x"], model="gpt-4o-mini")
        completion = Completion(
            text="x", model="gpt-4o-mini", usage=Usage(1_000_000, 0)
        )

        assert engine.cost_of(completion) == pytest.approx(0.15)

    def test_unknown_model_has_no_cost(self) -> None:
        assert Recording(["x"], model="no-such-model").estimate_cost(1000, 500) is None
