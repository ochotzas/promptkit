"""
YAML prompt loader for loading prompts from files.

This module provides functionality to load prompt definitions
from YAML files and convert them into Prompt objects.
"""

from pathlib import Path
from typing import Any, Dict

import yaml
from yaml.loader import SafeLoader

from promptkit.core.prompt import Prompt


def load_prompt(file_path: str | Path) -> Prompt:
    """
    Load a prompt from a YAML file.

    Args:
        file_path: Path to the YAML file containing the prompt definition.
                  The .yaml extension is optional and will be added automatically if missing.

    Returns:
        Prompt object created from the YAML file

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValidationError: If the prompt data is invalid

    Example:
        >>> prompt = load_prompt("examples/greet_user.yaml")
        >>> # Or without extension:
        >>> prompt = load_prompt("examples/greet_user")
        >>> response = prompt.render({"name": "Alice"})
    """
    file_path = Path(file_path)

    if not file_path.suffix:
        file_path = file_path.with_suffix(".yaml")
    elif file_path.suffix not in {".yaml", ".yml"}:
        file_path = file_path.with_suffix(file_path.suffix + ".yaml")

    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=SafeLoader)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML file {file_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a dictionary, got {type(data)}")

    return _create_prompt_from_dict(data, file_path)


def _create_prompt_from_dict(data: Dict[str, Any], file_path: Path) -> Prompt:
    """
    Create a Prompt object from a dictionary loaded from YAML.

    Args:
        data: Dictionary containing prompt data
        file_path: Path to the original file (for error reporting)

    Returns:
        Prompt object
    """
    required_fields = {"name", "description", "template"}
    missing_fields = required_fields - set(data.keys())

    if missing_fields:
        raise ValueError(
            f"Missing required fields in {file_path}: {', '.join(missing_fields)}"
        )

    # Ensure input_schema is present and is a dictionary
    if "input_schema" not in data:
        data["input_schema"] = {}
    elif not isinstance(data["input_schema"], dict):
        raise ValueError(
            f"input_schema must be a dictionary in {file_path}, "
            f"got {type(data['input_schema'])}"
        )

    try:
        return Prompt(**data)
    except Exception as e:
        raise ValueError(f"Failed to create prompt from {file_path}: {e}") from e


def save_prompt(prompt: Prompt, file_path: str | Path) -> None:
    """
    Save a prompt to a YAML file.

    Args:
        prompt: Prompt object to save
        file_path: Path where to save the YAML file

    Raises:
        OSError: If file writing fails
    """
    file_path = Path(file_path)

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "name": prompt.name,
        "description": prompt.description,
        "template": prompt.template,
        "input_schema": prompt.input_schema,
    }

    try:
        with file_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
    except OSError as e:
        raise OSError(f"Failed to save prompt to {file_path}: {e}") from e
