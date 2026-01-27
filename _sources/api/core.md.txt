# Core API Reference

## promptkit.core.prompt

### Prompt

```python
class Prompt(BaseModel):
    name: str
    description: str
    template: str
    input_schema: Dict[str, str]
```

#### Methods

**`render(inputs: Dict[str, Any], validate: bool = True) -> str`**

Render the template with inputs.

```python
prompt = Prompt(
    name="greet",
    description="Greeting",
    template="Hello {{ name }}!",
    input_schema={"name": "str"}
)
result = prompt.render({"name": "Alice"})
# "Hello Alice!"
```

**`validate_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]`**

Validate inputs against schema.

```python
validated = prompt.validate_inputs({"name": "Alice"})
```

**`get_required_inputs() -> list[str]`**

Get required input field names.

**`get_optional_inputs() -> list[str]`**

Get optional input field names.

## promptkit.core.loader

**`load_prompt(file_path: str | Path) -> Prompt`**

Load a prompt from YAML file.

```python
from promptkit import load_prompt

prompt = load_prompt("greeting.yaml")
prompt = load_prompt("greeting")  # .yaml extension optional
```

**`save_prompt(prompt: Prompt, file_path: str | Path) -> None`**

Save a prompt to YAML file.

```python
from promptkit.core.loader import save_prompt

save_prompt(prompt, "output.yaml")
```

## promptkit.core.runner

**`run_prompt(prompt, inputs, engine, validate_inputs=True) -> str`**

Execute a prompt with an engine.

```python
from promptkit import run_prompt

response = run_prompt(prompt, {"name": "Alice"}, engine)
```

**`run_prompt_async(prompt, inputs, engine, validate_inputs=True) -> str`**

Async version of run_prompt.

```python
response = await run_prompt_async(prompt, inputs, engine)
```

## promptkit.core.schema

**`validate_inputs(inputs, schema_dict) -> Dict[str, Any]`**

Validate inputs against a schema dictionary.

**`create_schema_model(schema_dict) -> Type[BaseModel]`**

Create a Pydantic model from schema.

## promptkit.core.compiler

### PromptCompiler

Handles Jinja2 template compilation.

```python
from promptkit.core.compiler import PromptCompiler

compiler = PromptCompiler()
template = compiler.compile_template("Hello {{ name }}!")
result = compiler.render_template(template, {"name": "Alice"})
```
