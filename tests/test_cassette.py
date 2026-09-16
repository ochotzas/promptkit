from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from promptkit.engines.base import BaseEngine
from promptkit.errors import EvalError
from promptkit.evals.cassette import (
    Cassette,
    CassetteEngine,
    OfflineEngine,
    cassette_path_for,
)
from promptkit.types import Completion, Message, Usage


class Live(BaseEngine):
    def __init__(self, text: str = "live", model: str = "gpt-4o-mini") -> None:
        super().__init__(model)
        self.calls = 0

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        self.calls += 1

        return Completion(
            text=self.text_for(messages), model=self.model, usage=Usage(9, 4)
        )

    def text_for(self, messages: list[Message]) -> str:
        return f"answer to {messages[-1].content}"


@pytest.fixture
def cassette(tmp_path: Path) -> Cassette:
    return Cassette.load(tmp_path / "suite.cassette.json")


class TestPaths:
    def test_suite_path_becomes_a_cassette_path(self) -> None:
        assert cassette_path_for("p/greet.evals.yaml").name == "greet.cassette.json"

    def test_prompt_path_becomes_a_cassette_path(self) -> None:
        assert cassette_path_for("p/greet.yaml").name == "greet.cassette.json"


class TestRecordAndReplay:
    def test_first_call_hits_the_engine(self, cassette: Cassette) -> None:
        engine = Live()
        wrapped = CassetteEngine(engine, cassette)
        wrapped.complete("hi")

        assert engine.calls == 1
        assert len(cassette) == 1

    def test_second_identical_call_is_replayed(self, cassette: Cassette) -> None:
        engine = Live()
        wrapped = CassetteEngine(engine, cassette)
        wrapped.complete("hi")
        wrapped.complete("hi")

        assert engine.calls == 1
        assert wrapped.hits == 1

    def test_a_different_call_is_recorded_separately(self, cassette: Cassette) -> None:
        engine = Live()
        wrapped = CassetteEngine(engine, cassette)
        wrapped.complete("hi")
        wrapped.complete("different")

        assert engine.calls == 2
        assert len(cassette) == 2

    def test_recording_survives_a_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        first = Cassette.load(path)
        CassetteEngine(Live(), first).complete("hi")
        first.save()

        reloaded = Cassette.load(path)

        assert len(reloaded) == 1

    def test_replay_needs_no_engine(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        recorded = Cassette.load(path)
        CassetteEngine(Live(), recorded).complete("hi")
        recorded.save()

        offline = CassetteEngine(OfflineEngine(), Cassette.load(path), mode="replay")

        assert offline.complete("hi").text == "answer to hi"

    def test_replay_mode_never_calls_the_engine(self, tmp_path: Path) -> None:
        engine = Live()
        wrapped = CassetteEngine(engine, Cassette.load(tmp_path / "s.json"), "replay")

        with pytest.raises(EvalError):
            wrapped.complete("hi")

        assert engine.calls == 0

    def test_record_mode_ignores_an_existing_recording(
        self, cassette: Cassette
    ) -> None:
        engine = Live()
        CassetteEngine(engine, cassette).complete("hi")
        CassetteEngine(engine, cassette, mode="record").complete("hi")

        assert engine.calls == 2

    def test_off_mode_bypasses_the_cassette(self, cassette: Cassette) -> None:
        engine = Live()
        wrapped = CassetteEngine(engine, cassette, mode="off")
        wrapped.complete("hi")
        wrapped.complete("hi")

        assert engine.calls == 2


class TestDiagnostics:
    def test_empty_cassette_says_so(self, tmp_path: Path) -> None:
        wrapped = CassetteEngine(
            OfflineEngine(), Cassette.load(tmp_path / "s.json"), "replay"
        )

        with pytest.raises(EvalError, match="is empty"):
            wrapped.complete("hi")

    def test_stale_cassette_blames_the_prompt(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        recorded = Cassette.load(path)
        CassetteEngine(Live(), recorded).complete("original prompt")
        recorded.save()

        stale = CassetteEngine(OfflineEngine(), Cassette.load(path), "replay")

        with pytest.raises(EvalError, match="changed since it was recorded"):
            stale.complete("edited prompt")

    def test_corrupt_cassette_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.cassette.json"
        path.write_text("{not json")

        with pytest.raises(EvalError, match="Could not read cassette"):
            Cassette.load(path)


class TestFidelity:
    def test_usage_survives_a_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        recorded = Cassette.load(path)
        CassetteEngine(Live(), recorded).complete("hi")
        recorded.save()

        replayed = Cassette.load(path)
        wrapped = CassetteEngine(OfflineEngine(), replayed, "replay")

        assert wrapped.complete("hi").usage == Usage(9, 4)

    def test_recorded_model_is_preserved(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        recorded = Cassette.load(path)
        CassetteEngine(Live(model="claude-sonnet-5"), recorded).complete("hi")
        recorded.save()

        wrapped = CassetteEngine(OfflineEngine(), Cassette.load(path), "replay")

        assert wrapped.complete("hi").model == "claude-sonnet-5"

    def test_key_is_independent_of_the_engine(self, tmp_path: Path) -> None:
        path = tmp_path / "s.cassette.json"
        recorded = Cassette.load(path)
        CassetteEngine(Live(model="gpt-4o-mini"), recorded).complete("hi")
        recorded.save()

        other = CassetteEngine(Live(model="claude-sonnet-5"), Cassette.load(path))

        assert other.complete("hi").text == "answer to hi"
