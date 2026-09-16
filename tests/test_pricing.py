from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from promptkit import pricing
from promptkit.utils.tokens import estimate_tokens


@pytest.fixture(autouse=True)
def _clear() -> Iterator[None]:
    pricing.clear_overrides()
    yield
    pricing.clear_overrides()


class TestLookup:
    def test_known_model(self) -> None:
        assert pricing.get_pricing("gpt-4o-mini") == pricing.PRICING["gpt-4o-mini"]

    def test_unknown_model(self) -> None:
        assert pricing.get_pricing("no-such-model") is None

    def test_dated_snapshot_resolves_to_its_base_model(self) -> None:
        assert pricing.get_pricing("claude-3-5-sonnet-20241022") == pricing.get_pricing(
            "claude-3-5-sonnet"
        )

    @pytest.mark.parametrize(
        "model",
        [
            "o3-pro",
            "o3-deep-research",
            "gpt-4o-audio-preview",
            "gpt-4.1-mini-preview",
            "claude-opus-4-turbocharged",
        ],
    )
    def test_unknown_variants_are_not_priced_by_prefix(self, model: str) -> None:
        assert pricing.get_pricing(model) is None

    def test_a_variant_is_never_priced_as_its_shorter_sibling(self) -> None:
        opus_45 = pricing.get_pricing("claude-opus-4-5")
        opus_4 = pricing.get_pricing("claude-opus-4-20250514")

        assert opus_45 is not None
        assert opus_4 is not None
        assert opus_45 != opus_4

    def test_override_takes_precedence(self) -> None:
        pricing.register_pricing("gpt-4o-mini", 99.0, 99.0)
        override = pricing.get_pricing("gpt-4o-mini")

        assert override is not None
        assert override.input_per_million == 99.0

    def test_override_adds_unknown_model(self) -> None:
        pricing.register_pricing("my-local-model", 0.0, 0.0)
        assert pricing.get_pricing("my-local-model") is not None

    def test_list_models_includes_overrides(self) -> None:
        pricing.register_pricing("zzz-model", 1.0, 1.0)
        assert "zzz-model" in pricing.list_models()


class TestLookupDetail:
    def test_exact_match_is_reported_as_exact(self) -> None:
        found = pricing.lookup("gpt-4o-mini")

        assert found is not None
        assert found.kind == "exact"
        assert found.exact is True
        assert found.matched == "gpt-4o-mini"

    def test_snapshot_match_is_reported_as_inferred(self) -> None:
        found = pricing.lookup("claude-3-5-sonnet-20241022")

        assert found is not None
        assert found.kind == "snapshot"
        assert found.exact is False
        assert found.matched == "claude-3-5-sonnet"
        assert "snapshot" in found.describe()

    def test_override_is_reported_as_an_override(self) -> None:
        pricing.register_pricing("my-model", 1.0, 2.0)
        found = pricing.lookup("my-model")

        assert found is not None
        assert found.kind == "override"
        assert "override" in found.describe()

    def test_override_wins_over_the_snapshot(self) -> None:
        pricing.register_pricing("gpt-4o-mini", 99.0, 99.0)
        found = pricing.lookup("gpt-4o-mini")

        assert found is not None
        assert found.pricing.input_per_million == 99.0

    def test_unknown_model_has_no_lookup(self) -> None:
        assert pricing.lookup("not-a-real-model") is None

    @pytest.mark.parametrize(
        ("model", "base"),
        [
            ("gpt-4o-mini-2024-07-18", "gpt-4o-mini"),
            ("claude-opus-4-20250514", "claude-opus-4"),
            ("mistral-large-latest", "mistral-large"),
        ],
    )
    def test_snapshot_suffixes_are_recognised(self, model: str, base: str) -> None:
        assert pricing.base_name(model) == base

    @pytest.mark.parametrize("model", ["o3-pro", "gpt-4o", "claude-opus-4-5"])
    def test_non_snapshot_names_are_left_alone(self, model: str) -> None:
        assert pricing.base_name(model) is None


class TestSnapshotData:
    def test_snapshot_has_a_date(self) -> None:
        assert pricing.PRICING_UPDATED != "unknown"
        assert len(pricing.PRICING_UPDATED) == 10

    def test_covers_the_engines_promptkit_ships(self) -> None:
        for model in (
            "gpt-4o-mini",
            "gpt-5",
            "claude-sonnet-5",
            "claude-opus-4-5",
            "claude-3-5-sonnet",
            "ollama",
        ):
            assert pricing.get_pricing(model) is not None, model

    def test_every_rate_is_a_non_negative_number(self) -> None:
        for name in pricing.list_models():
            rates = pricing.get_pricing(name)

            assert rates is not None, name
            assert rates.input_per_million >= 0.0, name
            assert rates.output_per_million >= 0.0, name

    def test_data_file_ships_with_the_package(self) -> None:
        assert pricing.DATA_FILE.is_file()


class TestCost:
    def test_cost_is_per_million_tokens(self) -> None:
        pricing.register_pricing("unit-test", 1.0, 2.0)
        assert pricing.estimate_cost(1_000_000, 0, "unit-test") == pytest.approx(1.0)
        assert pricing.estimate_cost(0, 1_000_000, "unit-test") == pytest.approx(2.0)

    def test_unknown_model_has_no_cost(self) -> None:
        assert pricing.estimate_cost(1000, 500, "no-such-model") is None

    def test_free_model(self) -> None:
        assert pricing.estimate_cost(1000, 500, "ollama") == 0.0

    def test_format_cost(self) -> None:
        assert pricing.format_cost(1.5) == "$1.5000"
        assert pricing.format_cost(0.000123) == "$0.000123"


class TestTokens:
    def test_empty(self) -> None:
        assert estimate_tokens("") == 0

    def test_grows_with_length(self) -> None:
        assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)

    def test_removed_helper_is_gone(self) -> None:
        import promptkit.utils.tokens as tokens

        assert not hasattr(tokens, "get_model_pricing")


class TestExactCounting:
    def test_tiktoken_is_detected(self) -> None:
        from promptkit.utils.tokens import has_exact_counting

        assert isinstance(has_exact_counting(), bool)

    def test_exact_beats_estimate_for_prose(self) -> None:
        from promptkit.utils.tokens import estimate_tokens, exact_tokens

        text = "The quick brown fox jumps over the lazy dog. " * 5
        exact = exact_tokens(text)

        if exact is None:
            pytest.skip("tiktoken not installed")

        assert exact > 0
        assert abs(exact - estimate_tokens(text)) < estimate_tokens(text)

    def test_empty_text(self) -> None:
        from promptkit.utils.tokens import exact_tokens

        assert exact_tokens("") == 0

    def test_unknown_model_falls_back_to_a_default_encoding(self) -> None:
        from promptkit.utils.tokens import exact_tokens

        counted = exact_tokens("hello there", "some-unreleased-model")

        if counted is None:
            pytest.skip("tiktoken not installed")

        assert counted > 0

    def test_count_tokens_always_returns_a_number(self) -> None:
        from promptkit.utils.tokens import count_tokens

        assert count_tokens("hello world") > 0


class TestSchemaModelCache:
    def test_repeat_compilation_is_cached(self) -> None:
        from promptkit.core.schema import clear_model_cache, compile_input_schema

        clear_model_cache()
        schema = {"name": "str", "age": "int"}

        assert compile_input_schema(schema) is compile_input_schema(schema)

    def test_different_schemas_get_different_models(self) -> None:
        from promptkit.core.schema import compile_input_schema

        assert compile_input_schema({"a": "str"}) is not compile_input_schema(
            {"a": "int"}
        )

    def test_empty_schema_has_no_model(self) -> None:
        from promptkit.core.schema import compile_input_schema

        assert compile_input_schema({}) is None

    def test_cache_is_bounded(self) -> None:
        from promptkit.core import schema as schema_module

        schema_module.clear_model_cache()

        for i in range(schema_module.MAX_MODEL_CACHE + 10):
            schema_module.compile_input_schema({f"f{i}": "str"})

        assert len(schema_module._model_cache) <= schema_module.MAX_MODEL_CACHE


class TestImmutability:
    def test_pricing_table_is_read_only(self) -> None:
        table: Any = pricing.PRICING

        with pytest.raises(TypeError):
            table["injected"] = pricing.ModelPricing(1.0, 1.0)

    def test_register_pricing_is_the_supported_path(self) -> None:
        pricing.register_pricing("bespoke-model", 1.0, 2.0)

        assert pricing.get_pricing("bespoke-model") == pricing.ModelPricing(1.0, 2.0)

    def test_overrides_do_not_touch_the_table(self) -> None:
        pricing.register_pricing("bespoke-model", 1.0, 2.0)

        assert "bespoke-model" not in pricing.PRICING


class TestOfflineTokenCounting:
    @pytest.fixture(autouse=True)
    def _clear_encoding_cache(self) -> Iterator[None]:
        from promptkit.utils.tokens import _encoding

        _encoding.cache_clear()
        yield
        _encoding.cache_clear()

    def _break_tiktoken(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tiktoken

        def unreachable(*args: Any, **kwargs: Any) -> Any:
            raise ConnectionError("tiktoken could not fetch its encoding")

        monkeypatch.setattr(tiktoken, "encoding_for_model", unreachable)
        monkeypatch.setattr(tiktoken, "get_encoding", unreachable)

    def test_exact_tokens_returns_none_when_unreachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.utils.tokens import exact_tokens

        self._break_tiktoken(monkeypatch)

        assert exact_tokens("hello world") is None

    def test_count_tokens_falls_back_to_the_heuristic(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.utils.tokens import count_tokens, estimate_tokens

        self._break_tiktoken(monkeypatch)
        text = "The quick brown fox jumps over the lazy dog."

        assert count_tokens(text) == estimate_tokens(text)

    def test_cost_estimation_still_works_offline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from promptkit.utils.tokens import count_tokens

        self._break_tiktoken(monkeypatch)

        cost = pricing.estimate_cost(count_tokens("hello"), 0, "gpt-4o-mini")

        assert cost is not None
        assert cost >= 0.0


class TestLazyPublicApi:
    def test_importing_promptkit_does_not_import_engines(self) -> None:
        import subprocess
        import sys

        code = (
            "import sys, promptkit;"
            "heavy = [m for m in sys.modules if m.startswith('promptkit.engines')];"
            "print(len(heavy))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )

        assert result.stdout.strip() == "0"

    def test_every_export_resolves(self) -> None:
        import promptkit

        for name in promptkit.__all__:
            assert getattr(promptkit, name) is not None, name

    def test_unknown_attribute_raises(self) -> None:
        import promptkit

        with pytest.raises(AttributeError, match="no attribute"):
            _ = promptkit.DefinitelyNotReal

    def test_dir_lists_the_public_api(self) -> None:
        import promptkit

        assert set(promptkit.__all__) <= set(dir(promptkit))
