from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from promptkit.core.jsonschema import compile_json_schema, looks_like_json_schema
from promptkit.errors import SchemaError


def obj(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}

    if required:
        schema["required"] = required

    return schema


class TestDetection:
    @pytest.mark.parametrize(
        ("schema", "expected"),
        [
            ({}, False),
            ({"name": "str"}, False),
            ({"name": "str | None"}, False),
            ({"type": "object", "properties": {}}, True),
            ({"properties": {"a": {"type": "string"}}}, True),
            ({"$schema": "https://json-schema.org/draft/2020-12/schema"}, True),
            ({"type": "string"}, True),
            ({"type": "str"}, False),
        ],
    )
    def test_detection(self, schema: dict[str, Any], expected: bool) -> None:
        assert looks_like_json_schema(schema) is expected


class TestScalars:
    @pytest.mark.parametrize(
        ("json_type", "value"),
        [("string", "x"), ("integer", 3), ("number", 1.5), ("boolean", True)],
    )
    def test_scalar_roundtrip(self, json_type: str, value: Any) -> None:
        model = compile_json_schema(obj({"f": {"type": json_type}}, ["f"]))

        assert model(f=value).model_dump()["f"] == value

    def test_required_field_is_enforced(self) -> None:
        model = compile_json_schema(obj({"f": {"type": "string"}}, ["f"]))

        with pytest.raises(ValidationError):
            model()

    def test_optional_field_defaults_to_none(self) -> None:
        model = compile_json_schema(obj({"f": {"type": "string"}}))

        assert model().model_dump()["f"] is None

    def test_declared_default_is_used(self) -> None:
        model = compile_json_schema(obj({"f": {"type": "integer", "default": 7}}))

        assert model().model_dump()["f"] == 7

    def test_description_is_carried_through(self) -> None:
        model = compile_json_schema(
            obj({"f": {"type": "string", "description": "the field"}}, ["f"])
        )

        assert model.model_fields["f"].description == "the field"

    def test_untyped_property_accepts_anything(self) -> None:
        model = compile_json_schema(obj({"f": {}}, ["f"]))

        assert model(f={"any": "thing"}).model_dump()["f"] == {"any": "thing"}


class TestArrays:
    def test_typed_items(self) -> None:
        model = compile_json_schema(
            obj({"tags": {"type": "array", "items": {"type": "string"}}}, ["tags"])
        )

        assert model(tags=["a", "b"]).model_dump()["tags"] == ["a", "b"]

    def test_item_type_is_enforced(self) -> None:
        model = compile_json_schema(
            obj({"tags": {"type": "array", "items": {"type": "integer"}}}, ["tags"])
        )

        with pytest.raises(ValidationError):
            model(tags=["not-an-int"])

    def test_untyped_items(self) -> None:
        model = compile_json_schema(obj({"tags": {"type": "array"}}, ["tags"]))

        assert model(tags=[1, "a"]).model_dump()["tags"] == [1, "a"]

    def test_array_of_objects(self) -> None:
        model = compile_json_schema(
            obj(
                {
                    "items": {
                        "type": "array",
                        "items": obj({"amount": {"type": "number"}}, ["amount"]),
                    }
                },
                ["items"],
            )
        )
        result = model(items=[{"amount": 1.5}])

        assert result.model_dump()["items"][0]["amount"] == 1.5


class TestNested:
    def test_nested_object(self) -> None:
        model = compile_json_schema(
            obj({"author": obj({"name": {"type": "string"}}, ["name"])}, ["author"])
        )

        assert model(author={"name": "Ada"}).model_dump()["author"] == {"name": "Ada"}

    def test_nested_required_is_enforced(self) -> None:
        model = compile_json_schema(
            obj({"author": obj({"name": {"type": "string"}}, ["name"])}, ["author"])
        )

        with pytest.raises(ValidationError):
            model(author={})

    def test_free_form_object(self) -> None:
        model = compile_json_schema(obj({"extra": {"type": "object"}}, ["extra"]))

        assert model(extra={"a": 1}).model_dump()["extra"] == {"a": 1}


class TestEnums:
    def test_string_enum(self) -> None:
        model = compile_json_schema(obj({"s": {"enum": ["a", "b"]}}, ["s"]))

        assert model(s="a").model_dump()["s"] == "a"

    def test_string_enum_rejects_other_values(self) -> None:
        model = compile_json_schema(obj({"s": {"enum": ["a", "b"]}}, ["s"]))

        with pytest.raises(ValidationError):
            model(s="c")

    def test_numeric_enum(self) -> None:
        model = compile_json_schema(obj({"n": {"enum": [1, 2]}}, ["n"]))

        assert model(n=1) is not None

    def test_empty_enum_is_rejected(self) -> None:
        with pytest.raises(SchemaError, match="non-empty"):
            compile_json_schema(obj({"s": {"enum": []}}, ["s"]))


class TestUnionsAndRefs:
    def test_type_list_becomes_a_union(self) -> None:
        model = compile_json_schema(obj({"f": {"type": ["string", "integer"]}}, ["f"]))

        assert model(f="x").model_dump()["f"] == "x"
        assert model(f=3).model_dump()["f"] == 3

    def test_nullable_via_type_list(self) -> None:
        model = compile_json_schema(obj({"f": {"type": ["string", "null"]}}, ["f"]))

        assert model(f=None).model_dump()["f"] is None

    def test_local_ref_is_resolved(self) -> None:
        schema = {
            "type": "object",
            "properties": {"author": {"$ref": "#/$defs/Person"}},
            "required": ["author"],
            "$defs": {"Person": obj({"name": {"type": "string"}}, ["name"])},
        }
        model = compile_json_schema(schema)

        assert model(author={"name": "Ada"}).model_dump()["author"]["name"] == "Ada"

    def test_definitions_key_also_works(self) -> None:
        schema = {
            "type": "object",
            "properties": {"a": {"$ref": "#/definitions/T"}},
            "required": ["a"],
            "definitions": {"T": {"type": "string"}},
        }

        assert compile_json_schema(schema)(a="x").model_dump()["a"] == "x"

    def test_remote_ref_is_rejected(self) -> None:
        schema = obj({"a": {"$ref": "https://example.com/x.json"}}, ["a"])

        with pytest.raises(SchemaError, match="local"):
            compile_json_schema(schema)

    def test_unresolvable_ref_is_rejected(self) -> None:
        schema = obj({"a": {"$ref": "#/$defs/Missing"}}, ["a"])

        with pytest.raises(SchemaError, match="could not be resolved"):
            compile_json_schema(schema)


class TestRejections:
    def test_non_object_root_is_rejected(self) -> None:
        with pytest.raises(SchemaError, match="must be an object"):
            compile_json_schema({"type": "array"})

    def test_missing_properties_is_rejected(self) -> None:
        with pytest.raises(SchemaError, match="no 'properties'"):
            compile_json_schema({"type": "object"})

    def test_non_mapping_property_is_rejected(self) -> None:
        with pytest.raises(SchemaError, match="must be a mapping"):
            compile_json_schema({"type": "object", "properties": {"a": "string"}})

    def test_unknown_type_is_rejected_by_name(self) -> None:
        with pytest.raises(SchemaError) as exc:
            compile_json_schema(obj({"a": {"type": "decimal"}}, ["a"]))

        assert exc.value.field == "a"
        assert "decimal" in str(exc.value)
