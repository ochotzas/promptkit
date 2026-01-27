# CLI Reference

## Installation

The CLI is available after installing PromptKit:

```bash
pip install promptkit-core
promptkit --help
```

## Commands

### `run` - Execute a Prompt

```bash
promptkit run PROMPT_FILE [OPTIONS]
```

Options:
- `--key`, `-k`: OpenAI API key (or set OPENAI_API_KEY)
- `--model`, `-m`: Model name (default: gpt-4o-mini)
- `--engine`, `-e`: Engine to use: openai, ollama (default: openai)
- `--temperature`, `-t`: Temperature 0.0-2.0 (default: 0.7)
- `--max-tokens`: Max tokens to generate
- `--verbose`, `-v`: Enable verbose logging
- `--name`: Name variable
- `--context`: Context variable

```bash
promptkit run greet.yaml --name Alice
promptkit run greet.yaml --engine ollama --model llama2 --name Bob
```

### `render` - Render Template

Render a prompt without calling an LLM.

```bash
promptkit render PROMPT_FILE [OPTIONS]
```

Options:
- `--output`, `-o`: Save to file
- `--name`: Name variable
- `--context`: Context variable
- `--vars`: JSON string of variables
- `--interactive`, `-i`: Prompt for missing variables

```bash
promptkit render greet.yaml --name Alice
promptkit render greet.yaml --vars '{"name": "Alice"}'
promptkit render greet.yaml --interactive
```

### `lint` - Validate Prompt

Check prompt file structure.

```bash
promptkit lint PROMPT_FILE
```

```bash
promptkit lint greet.yaml
```

### `info` - Prompt Information

Display detailed prompt information.

```bash
promptkit info PROMPT_FILE
```

```bash
promptkit info greet.yaml
```

### `cost` - Cost Estimation

Estimate cost before execution.

```bash
promptkit cost PROMPT_FILE [OPTIONS]
```

Options:
- `--model`, `-m`: Model for estimation (default: gpt-4o-mini)
- `--output-tokens`: Expected output tokens (default: 500)
- `--name`: Name variable
- `--context`: Context variable

```bash
promptkit cost greet.yaml --model gpt-4 --name Alice
```

## Environment Variables

- `OPENAI_API_KEY`: Default OpenAI API key
