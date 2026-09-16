from __future__ import annotations

from pathlib import Path

import pytest

from promptkit.cache import Cache, DiskCache, MemoryCache, make_key
from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.base import BaseEngine
from promptkit.types import Completion, Message, Usage

MESSAGES = [Message("user", "hello")]


class Counting(BaseEngine):
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        super().__init__(model)
        self.calls = 0

    def _complete(self, messages: list[Message], **options: object) -> Completion:
        self.calls += 1

        return Completion(text="response", model=self.model, usage=Usage(5, 2))


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="t", description="d", template="Hi {{ n }}", input_schema={"n": "str"}
    )


class TestKey:
    def test_stable_for_same_inputs(self) -> None:
        assert make_key(MESSAGES, "m", {"temperature": 0.7}) == make_key(
            MESSAGES, "m", {"temperature": 0.7}
        )

    def test_varies_with_content(self) -> None:
        assert make_key(MESSAGES, "m") != make_key([Message("user", "other")], "m")

    def test_varies_with_model(self) -> None:
        assert make_key(MESSAGES, "a") != make_key(MESSAGES, "b")

    def test_varies_with_namespace(self) -> None:
        assert make_key(MESSAGES, "m", namespace="a") != make_key(
            MESSAGES, "m", namespace="b"
        )

    def test_option_order_does_not_matter(self) -> None:
        assert make_key(MESSAGES, "m", {"a": 1, "b": 2}) == make_key(
            MESSAGES, "m", {"b": 2, "a": 1}
        )

    @pytest.mark.parametrize(
        "secret_key", ["api_key", "key", "authorization", "token", "secret"]
    )
    def test_secrets_never_enter_the_key(self, secret_key: str) -> None:
        with_secret = make_key(MESSAGES, "m", {"temperature": 0.7, secret_key: "shh"})
        without = make_key(MESSAGES, "m", {"temperature": 0.7})

        assert with_secret == without

    def test_none_options_ignored(self) -> None:
        assert make_key(MESSAGES, "m", {"seed": None}) == make_key(MESSAGES, "m", {})


class TestMemoryCache:
    def test_roundtrip(self) -> None:
        cache = MemoryCache()
        completion = Completion(text="x", model="m")
        cache.set("k", completion)

        assert cache.get("k") == completion

    def test_miss_returns_none(self) -> None:
        assert MemoryCache().get("nope") is None

    def test_eviction_is_bounded(self) -> None:
        cache = MemoryCache(max_entries=2)

        for i in range(5):
            cache.set(str(i), Completion(text=str(i), model="m"))

        assert len(cache) == 2

    def test_satisfies_protocol(self) -> None:
        assert isinstance(MemoryCache(), Cache)


class TestDiskCache:
    def test_roundtrip(self, tmp_path: Path) -> None:
        cache = DiskCache(tmp_path)
        cache.set("k", Completion(text="x", model="m", usage=Usage(3, 1)))
        hit = cache.get("k")

        assert hit is not None
        assert hit.text == "x"
        assert hit.usage == Usage(3, 1)

    def test_miss_returns_none(self, tmp_path: Path) -> None:
        assert DiskCache(tmp_path).get("nope") is None

    def test_corrupt_entry_is_a_miss(self, tmp_path: Path) -> None:
        cache = DiskCache(tmp_path)
        (tmp_path / "bad.json").write_text("{not json")

        assert cache.get("bad") is None

    def test_survives_process_boundary(self, tmp_path: Path) -> None:
        DiskCache(tmp_path).set("k", Completion(text="persisted", model="m"))
        reopened = DiskCache(tmp_path).get("k")

        assert reopened is not None
        assert reopened.text == "persisted"

    def test_satisfies_protocol(self, tmp_path: Path) -> None:
        assert isinstance(DiskCache(tmp_path), Cache)


class TestRunnerCaching:
    def test_second_identical_call_is_served_from_cache(self, prompt: Prompt) -> None:
        engine = Counting()
        cache = MemoryCache()
        run_prompt(prompt, {"n": "A"}, engine, cache=cache)
        run_prompt(prompt, {"n": "A"}, engine, cache=cache)

        assert engine.calls == 1

    def test_empty_cache_is_not_treated_as_absent(self, prompt: Prompt) -> None:
        engine = Counting()
        cache = MemoryCache()

        assert len(cache) == 0

        run_prompt(prompt, {"n": "A"}, engine, cache=cache)

        assert len(cache) == 1

    def test_different_inputs_miss(self, prompt: Prompt) -> None:
        engine = Counting()
        cache = MemoryCache()
        run_prompt(prompt, {"n": "A"}, engine, cache=cache)
        run_prompt(prompt, {"n": "B"}, engine, cache=cache)

        assert engine.calls == 2

    def test_no_cache_always_calls(self, prompt: Prompt) -> None:
        engine = Counting()
        run_prompt(prompt, {"n": "A"}, engine)
        run_prompt(prompt, {"n": "A"}, engine)

        assert engine.calls == 2
