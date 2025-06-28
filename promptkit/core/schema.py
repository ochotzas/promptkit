"""
Schema validation utilities using Pydantic.

This module provides functionality to validate prompt inputs against
defined schemas, ensuring type safety and proper data validation.
"""

from typing import Any, Dict, Type, Union

from pydantic import BaseModel, ValidationError, create_model


def create_schema_model(schema_dict: Dict[str, str]) -> Type[BaseModel]:
    """
    Create a Pydantic model from a schema dictionary.

    Args:
        schema_dict: Dictionary mapping field names to type strings

    Returns:
        Pydantic model class for validation

    Example:
        >>> schema = {"name": "str", "age": "int"}
        >>> Model = create_schema_model(schema)
        >>> instance = Model(name="Alice", age=30)
    """
    field_definitions = {}

    for field_name, type_str in schema_dict.items():
        python_type = _parse_type_string(type_str)

        if " | None" in type_str:
            field_definitions[field_name] = (python_type, None)
        else:
            field_definitions[field_name] = python_type

    # Use type: ignore to handle mypy limitations with dynamic model creation
    return create_model("DynamicSchema", **field_definitions)  # type: ignore[no-any-return,call-overload]


def _parse_type_string(type_str: str) -> Any:  # type: ignore[misc]
    """
    Parse a type string into a Python type.

    Supports: str, int, float, bool, list, dict
    Also supports optional types like "str | None"
    """
    type_str = type_str.strip()

    # Handle optional types (Union with None)
    if " | None" in type_str:
        base_type_str = type_str.replace(" | None", "").strip()
        base_type = _parse_basic_type(base_type_str)
        return Union[base_type, type(None)]  # type: ignore[return-value]

    return _parse_basic_type(type_str)


def _parse_basic_type(type_str: str) -> Any:
    """Parse basic type strings to Python types."""
    type_mapping = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    if type_str in type_mapping:
        return type_mapping[type_str]

    raise ValueError(f"Unsupported type: {type_str}")


def validate_inputs(
    inputs: Dict[str, Any], schema_dict: Dict[str, str]
) -> Dict[str, Any]:
    """
    Validate inputs against a schema dictionary.

    Args:
        inputs: Input data to validate
        schema_dict: Schema definition

    Returns:
        Validated input data

    Raises:
        ValidationError: If validation fails
    """
    if not schema_dict:
        return inputs

    try:
        SchemaModel = create_schema_model(schema_dict)
        validated = SchemaModel(**inputs)
        result: Dict[str, Any] = validated.model_dump()
        return result
    except ValidationError as e:
        raise e  # Re-raise the original Pydantic ValidationError
    except Exception as e:
        raise ValueError(f"Input validation failed: {e}") from e
