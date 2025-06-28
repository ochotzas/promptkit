# Core API Reference

Complete reference for PromptKit's core modules and classes.

## promptkit.core.prompt

### Prompt Class

The main class for representing and working with prompts.

```python
class Prompt:
    """
    Represents a structured prompt with template, schema, and metadata.

    Attributes:
        name (str): Unique identifier for the prompt
        description (str): Human-readable description
        template (str): Jinja2 template string
        input_schema (dict): JSON schema for input validation
        metadata (dict): Additional metadata
    """

    def __init__(
        self,
        name: str,
        template: str,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new Prompt instance.

        Args:
            name: Unique identifier for the prompt
            template: Jinja2 template string
            description: Human-readable description
            input_schema: JSON schema for input validation
            metadata: Additional metadata dictionary
        """

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input data against the prompt's schema.

        Args:
            input_data: Dictionary of input values

        Returns:
            Validated and potentially transformed input data

        Raises:
            ValidationError: If input data doesn't match schema
        """

    def render_template(self, input_data: Dict[str, Any]) -> str:
        """
        Render the template with provided input data.

        Args:
            input_data: Dictionary of values for template variables

        Returns:
            Rendered template string

        Raises:
            TemplateError: If template rendering fails
        """

    def estimate_tokens(self, input_data: Dict[str, Any]) -> int:
        """
        Estimate token count for the rendered prompt.

        Args:
            input_data: Dictionary of input values

        Returns:
            Estimated token count
        """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert prompt to dictionary representation.

        Returns:
            Dictionary containing all prompt data
        """

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """
        Create Prompt instance from dictionary.

        Args:
            data: Dictionary containing prompt data

        Returns:
            New Prompt instance
        """
```

## promptkit.core.loader

### Functions

```python
def load_prompt(file_path: str) -> Prompt:
    """
    Load a prompt from a YAML file.

    Args:
        file_path: Path to the YAML prompt file

    Returns:
        Prompt instance

    Raises:
        FileNotFoundError: If file doesn't exist
        YAMLError: If file contains invalid YAML
        ValidationError: If prompt structure is invalid
    """

def load_prompts_from_directory(directory_path: str) -> Dict[str, Prompt]:
    """
    Load all prompts from a directory.

    Args:
        directory_path: Path to directory containing prompt files

    Returns:
        Dictionary mapping prompt names to Prompt instances

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
    """

def save_prompt(prompt: Prompt, file_path: str) -> None:
    """
    Save a prompt to a YAML file.

    Args:
        prompt: Prompt instance to save
        file_path: Path where to save the file

    Raises:
        IOError: If file cannot be written
    """
```

### PromptRegistry Class

```python
class PromptRegistry:
    """
    Registry for managing multiple prompts.
    """

    def __init__(self):
        """Initialize empty registry."""

    def register(self, prompt: Prompt) -> None:
        """
        Register a prompt in the registry.

        Args:
            prompt: Prompt to register

        Raises:
            DuplicatePromptError: If prompt name already exists
        """

    def get(self, name: str) -> Prompt:
        """
        Get a prompt by name.

        Args:
            name: Name of the prompt

        Returns:
            Prompt instance

        Raises:
            PromptNotFoundError: If prompt doesn't exist
        """

    def list_prompts(self) -> List[str]:
        """
        List all registered prompt names.

        Returns:
            List of prompt names
        """

    def remove(self, name: str) -> None:
        """
        Remove a prompt from the registry.

        Args:
            name: Name of the prompt to remove

        Raises:
            PromptNotFoundError: If prompt doesn't exist
        """

    def load_directory(self, directory_path: str) -> None:
        """
        Load all prompts from a directory into the registry.

        Args:
            directory_path: Path to directory containing prompts

        Raises:
            DirectoryNotFoundError: If directory doesn't exist
        """
```

## promptkit.core.runner

### Functions

```python
def run_prompt(
    prompt: Prompt,
    input_data: Dict[str, Any],
    engine: BaseEngine,
    **kwargs
) -> str:
    """
    Execute a prompt with the given engine.

    Args:
        prompt: Prompt to execute
        input_data: Input data for the prompt
        engine: Engine to use for execution
        **kwargs: Additional arguments passed to engine

    Returns:
        Engine response string

    Raises:
        ValidationError: If input data is invalid
        EngineError: If engine execution fails
    """

async def run_prompt_async(
    prompt: Prompt,
    input_data: Dict[str, Any],
    engine: BaseEngine,
    **kwargs
) -> str:
    """
    Asynchronously execute a prompt with the given engine.

    Args:
        prompt: Prompt to execute
        input_data: Input data for the prompt
        engine: Engine to use for execution
        **kwargs: Additional arguments passed to engine

    Returns:
        Engine response string

    Raises:
        ValidationError: If input data is invalid
        EngineError: If engine execution fails
    """

def batch_run_prompts(
    prompt_requests: List[Dict[str, Any]],
    engine: BaseEngine,
    max_workers: int = 5
) -> List[str]:
    """
    Execute multiple prompts in parallel.

    Args:
        prompt_requests: List of dicts with 'prompt', 'input_data' keys
        engine: Engine to use for execution
        max_workers: Maximum number of concurrent workers

    Returns:
        List of response strings in order

    Raises:
        ValidationError: If any input data is invalid
        EngineError: If any engine execution fails
    """
```

### PromptRunner Class

```python
class PromptRunner:
    """
    Advanced prompt execution with caching and retry logic.
    """

    def __init__(
        self,
        engine: BaseEngine,
        cache_ttl: int = 3600,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize PromptRunner.

        Args:
            engine: Engine to use for execution
            cache_ttl: Cache time-to-live in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """

    def run(
        self,
        prompt: Prompt,
        input_data: Dict[str, Any],
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """
        Execute prompt with caching and retry logic.

        Args:
            prompt: Prompt to execute
            input_data: Input data for the prompt
            use_cache: Whether to use response caching
            **kwargs: Additional arguments passed to engine

        Returns:
            Engine response string
        """

    def clear_cache(self) -> None:
        """Clear the response cache."""

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit/miss counts
        """
```

## promptkit.core.template

### TemplateRenderer Class

```python
class TemplateRenderer:
    """
    Jinja2-based template renderer with custom extensions.
    """

    def __init__(
        self,
        template_dir: Optional[str] = None,
        auto_escape: bool = False
    ):
        """
        Initialize template renderer.

        Args:
            template_dir: Directory for template includes/inheritance
            auto_escape: Whether to auto-escape template output
        """

    def render(
        self,
        template: str,
        context: Dict[str, Any],
        functions: Optional[Dict[str, Callable]] = None
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: Template string
            context: Variables available in template
            functions: Custom functions available in template

        Returns:
            Rendered template string

        Raises:
            TemplateError: If template rendering fails
        """

    def add_filter(self, name: str, func: Callable) -> None:
        """
        Add a custom template filter.

        Args:
            name: Filter name
            func: Filter function
        """

    def add_function(self, name: str, func: Callable) -> None:
        """
        Add a custom template function.

        Args:
            name: Function name
            func: Function to add
        """

    def compile_template(self, template: str) -> 'CompiledTemplate':
        """
        Compile template for reuse.

        Args:
            template: Template string

        Returns:
            Compiled template object
        """
```

## promptkit.core.validation

### Validator Class

```python
class Validator:
    """
    Input validation using JSON Schema.
    """

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize validator with schema.

        Args:
            schema: JSON schema for validation
        """

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against schema.

        Args:
            data: Data to validate

        Returns:
            Validated (and potentially coerced) data

        Raises:
            ValidationError: If validation fails
        """

    def validate_partial(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data allowing missing required fields.

        Args:
            data: Data to validate

        Returns:
            Validated data

        Raises:
            ValidationError: If validation fails
        """

    def get_default_values(self) -> Dict[str, Any]:
        """
        Get default values from schema.

        Returns:
            Dictionary of default values
        """
```

### Functions

```python
def create_schema_from_example(example_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate JSON schema from example data.

    Args:
        example_data: Example input data

    Returns:
        Generated JSON schema
    """

def validate_schema(schema: Dict[str, Any]) -> bool:
    """
    Validate that a schema is well-formed.

    Args:
        schema: Schema to validate

    Returns:
        True if valid schema

    Raises:
        SchemaError: If schema is invalid
    """

def merge_schemas(*schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple schemas into one.

    Args:
        *schemas: Schemas to merge

    Returns:
        Merged schema
    """
```

## promptkit.core.exceptions

### Custom Exceptions

```python
class PromptKitError(Exception):
    """Base exception for all PromptKit errors."""

class ValidationError(PromptKitError):
    """Raised when input validation fails."""

    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message)
        self.errors = errors or []

class TemplateError(PromptKitError):
    """Raised when template rendering fails."""

class EngineError(PromptKitError):
    """Raised when engine execution fails."""

class PromptNotFoundError(PromptKitError):
    """Raised when a prompt cannot be found."""

class DuplicatePromptError(PromptKitError):
    """Raised when trying to register a duplicate prompt."""

class SchemaError(PromptKitError):
    """Raised when schema validation fails."""

class ConfigurationError(PromptKitError):
    """Raised when configuration is invalid."""
```

## promptkit.core.utils

### Utility Functions

```python
def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate token count for text.

    Args:
        text: Text to count tokens for
        model: Model to use for estimation

    Returns:
        Estimated token count
    """

def calculate_cost(tokens: int, model: str = "gpt-3.5-turbo") -> float:
    """
    Calculate estimated cost for token usage.

    Args:
        tokens: Number of tokens
        model: Model to calculate cost for

    Returns:
        Estimated cost in USD
    """

def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize input data by removing dangerous content.

    Args:
        data: Input data to sanitize

    Returns:
        Sanitized data
    """

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary

    Returns:
        Merged dictionary
    """

def get_version() -> str:
    """
    Get PromptKit version.

    Returns:
        Version string
    """

def generate_prompt_id() -> str:
    """
    Generate unique prompt identifier.

    Returns:
        Unique ID string
    """
```

## Type Definitions

```python
from typing import Dict, Any, List, Optional, Union, Callable

# Common type aliases
PromptData = Dict[str, Any]
SchemaDict = Dict[str, Any]
InputData = Dict[str, Any]
TemplateContext = Dict[str, Any]
ValidationErrors = List[Dict[str, Any]]

# Engine response types
EngineResponse = Union[str, Dict[str, Any]]
StreamingResponse = Iterator[str]

# Configuration types
EngineConfig = Dict[str, Any]
CacheConfig = Dict[str, Any]
```

This reference covers all the core functionality available in PromptKit's main modules. For engine-specific APIs, see the [Engines API Reference](engines.md).
