from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from promptkit.core.prompt import Prompt
from promptkit.core.runner import run_structured, run_structured_async
from promptkit.core.structured import (
    ParsedCompletion,
    extract_json,
    parse_output,
    prepare,
    schema_instruction,
)
from promptkit.engines.base import BaseEngine
from promptkit.errors import OutputValidationError
from promptkit.events import ParseRetried, Recorder, listening
from promptkit.types import Capabilities, Completion, Message, Usage


class Invoice(BaseModel):
    number: str
    total: float


class Scripted(BaseEngine):
    capabilities = Capabilities(streaming=False, json_mode=False, system_role=True)

    def __init__(self, replies: list[str], **kw: Any) -> None:
        super().__init__("test", **kw)
        self.replies = list(replies)
        self.sent: list[list[Message]] = []
        self.options: list[dict[str, Any]] = []

    def _complete(self, messages: list[Message], **options: Any) -> Completion:
        self.sent.append(list(messages))
        self.options.append(options)

        return Completion(text=self.replies.pop(0), model=self.model, usage=Usage(1, 1))

    async def _acomplete(self, messages: list[Message], **options: Any) -> Completion:
        return self._complete(messages, **options)


class JsonMode(Scripted):
    capabilities = Capabilities(streaming=False, json_mode=True, system_role=True)


@pytest.fixture
def prompt() -> Prompt:
    return Prompt(
        name="inv",
        description="d",
        template="Extract from {{ doc }}",
        input_schema={"doc": "str"},
    )


@pytest.fixture
def schema_prompt() -> Prompt:
    return Prompt(
        name="inv",
        description="d",
        template="Extract from {{ doc }}",
        input_schema={"doc": "str"},
        output_schema={
            "type": "object",
            "required": ["number", "total"],
            "properties": {"number": {"type": "string"}, "total": {"type": "number"}},
        },
    )


class TestExtraction:
    @pytest.mark.parametrize(
        "text",
        [
            '{"number":"A-1","total":9.5}',
            '```json\n{"number":"A-1","total":9.5}\n```',
            '```\n{"number":"A-1","total":9.5}\n```',
            'Sure! {"number":"A-1","total":9.5} hope that helps',
            '   {"number":"A-1","total":9.5}   ',
        ],
    )
    def test_json_is_recovered(self, text: str) -> None:
        assert parse_output(text, Invoice) == Invoice(number="A-1", total=9.5)

    def test_array_payload_is_extracted(self) -> None:
        assert extract_json("noise [1,2] tail") == "[1,2]"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(OutputValidationError, match="not valid JSON"):
            parse_output("definitely not json", Invoice)

    def test_non_object_json_raises(self) -> None:
        with pytest.raises(OutputValidationError, match="must be a JSON object"):
            parse_output("[1, 2, 3]", Invoice)

    def test_schema_mismatch_raises(self) -> None:
        with pytest.raises(OutputValidationError, match="did not match"):
            parse_output('{"number": 1}', Invoice)


class TestPreparation:
    def test_json_mode_sends_the_schema_as_an_option(self) -> None:
        messages, extra = prepare([Message("user", "x")], Invoice, json_mode=True)

        assert len(messages) == 1
        assert extra["json_schema"]["type"] == "object"

    def test_without_json_mode_a_schema_instruction_is_appended(self) -> None:
        messages, extra = prepare([Message("user", "x")], Invoice, json_mode=False)

        assert extra == {}
        assert len(messages) == 2
        assert messages[-1].role == "system"
        assert "JSON Schema" in messages[-1].content

    def test_instruction_contains_the_schema(self) -> None:
        assert "number" in schema_instruction(Invoice)


class TestRunStructured:
    def test_first_attempt_succeeds(self, prompt: Prompt) -> None:
        engine = Scripted(['{"number":"A-1","total":9.5}'])
        result = run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)

        assert isinstance(result, ParsedCompletion)
        assert result.value == Invoice(number="A-1", total=9.5)
        assert len(engine.sent) == 1

    def test_result_exposes_the_raw_completion(self, prompt: Prompt) -> None:
        engine = Scripted(['{"number":"A-1","total":9.5}'])
        result = run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)

        assert result.completion.usage == Usage(1, 1)
        assert str(result) == result.text

    def test_bad_output_is_repaired(self, prompt: Prompt) -> None:
        engine = Scripted(["nonsense", '{"number":"A-1","total":9.5}'])
        result = run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)

        assert result.value.number == "A-1"
        assert len(engine.sent) == 2
        assert len(engine.sent[1]) > len(engine.sent[0])

    def test_repair_message_includes_the_error(self, prompt: Prompt) -> None:
        engine = Scripted(["nonsense", '{"number":"A-1","total":9.5}'])
        run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)
        repair = engine.sent[1][-1]

        assert repair.role == "user"
        assert "could not be parsed" in repair.content

    def test_retry_budget_is_respected(self, prompt: Prompt) -> None:
        engine = Scripted(["bad", "still bad", "worse"])

        with pytest.raises(OutputValidationError):
            run_structured(
                prompt,
                {"doc": "x"},
                engine,
                output_model=Invoice,
                max_parse_retries=2,
            )

        assert len(engine.sent) == 3

    def test_zero_retries_fails_immediately(self, prompt: Prompt) -> None:
        engine = Scripted(["bad"])

        with pytest.raises(OutputValidationError):
            run_structured(
                prompt,
                {"doc": "x"},
                engine,
                output_model=Invoice,
                max_parse_retries=0,
            )

        assert len(engine.sent) == 1

    def test_parse_retry_event_is_emitted(self, prompt: Prompt) -> None:
        engine = Scripted(["bad", '{"number":"A-1","total":9.5}'])
        recorder = Recorder()

        with listening(recorder):
            run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)

        retries = recorder.of(ParseRetried)

        assert len(retries) == 1
        assert retries[0].attempt == 1

    def test_json_mode_engine_gets_the_schema_option(self, prompt: Prompt) -> None:
        engine = JsonMode(['{"number":"A-1","total":9.5}'])
        run_structured(prompt, {"doc": "x"}, engine, output_model=Invoice)

        assert "json_schema" in engine.options[0]
        assert len(engine.sent[0]) == 1

    def test_output_schema_from_the_prompt_is_used(self, schema_prompt: Prompt) -> None:
        engine = Scripted(['{"number":"A-1","total":9.5}'])
        result = run_structured(schema_prompt, {"doc": "x"}, engine)

        assert result.value.number == "A-1"

    def test_explicit_model_overrides_the_prompt_schema(
        self, schema_prompt: Prompt
    ) -> None:
        engine = Scripted(['{"number":"A-1","total":9.5}'])
        result = run_structured(
            schema_prompt, {"doc": "x"}, engine, output_model=Invoice
        )

        assert isinstance(result.value, Invoice)

    def test_no_schema_anywhere_is_an_error(self, prompt: Prompt) -> None:
        with pytest.raises(OutputValidationError, match="no output_schema"):
            run_structured(prompt, {"doc": "x"}, Scripted(["{}"]))

    def test_input_validation_still_applies(self, prompt: Prompt) -> None:
        from promptkit.errors import InputValidationError

        with pytest.raises(InputValidationError):
            run_structured(prompt, {}, Scripted(["{}"]), output_model=Invoice)


class TestAsync:
    def test_async_structured_run(self, prompt: Prompt) -> None:
        import asyncio

        engine = Scripted(['{"number":"A-1","total":9.5}'])
        result = asyncio.run(
            run_structured_async(prompt, {"doc": "x"}, engine, output_model=Invoice)
        )

        assert result.value.total == 9.5

    def test_async_repair_loop(self, prompt: Prompt) -> None:
        import asyncio

        engine = Scripted(["bad", '{"number":"A-1","total":9.5}'])
        result = asyncio.run(
            run_structured_async(prompt, {"doc": "x"}, engine, output_model=Invoice)
        )

        assert result.value.number == "A-1"
        assert len(engine.sent) == 2
