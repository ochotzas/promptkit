<br/>
<p align="center">
  <h1 align="center">⚙️ PromptKit</h1>
</p>

<p align="center" style="font-size:1.15em;">
  A production-grade library for structured LLM prompt engineering.
  <br/>
  <br/>
  <img src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExNnA2ZzlxYnIzaW53dDUyZnVlY3JkcG5qNnpsZHlvbmhnYmdpaHQ0bSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3oKIPnAiaMCws8nOsE/giphy.gif" alt="Cat Typing on Computer" width="100" style="border-radius:7px;box-shadow:0 1px 4px #0001;opacity:0.85;margin-bottom:-6px;margin-top:6px;" />
  <br/>
  <a href="https://ochotzas.github.io/promptkit/" style="margin-top:2px;"><strong>Explore the docs »</strong></a>
  <br/>
  <br/>
  <a href="https://github.com/ochotzas/promptkit/issues">Report Bug</a>
  ·
  <a href="https://github.com/ochotzas/promptkit/issues">Request Feature</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/promptkit-core/"> <img alt="PyPI" src="https://img.shields.io/pypi/v/promptkit-core.svg?style=flat-square"></a>
  <a href="https://img.shields.io/badge/python-%3E%3D3.10-blue"><img alt="PyPI - Python Version" src="https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square"></a>
  <a href="https://img.shields.io/pypi/pyreq/promptkit-core?style=flat-square" alt="PyPI - Python Required Version"></a>
  <a href="https://github.com/ochotzas/promptkit/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/ochotzas/promptkit/ci.yml?branch=main&style=flat-square&label=tests"></a>
  <a href="https://github.com/ochotzas/promptkit/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/ochotzas/promptkit.svg?style=flat-square"></a>
</p>

-----

## Why PromptKit?

Managing prompts for Large Language Models (LLMs) can quickly become messy. Hardcoding prompts as f-strings mixes logic with presentation, lacks validation, and makes it difficult to reuse and test them.

**PromptKit** solves this by treating your prompts as structured, version-controlled assets. By defining prompts in simple `YAML` files, you get:

  * **Clean Separation:** Your prompt templates, logic, and configuration are separate from your application code.
  * **Safety & Reliability:** Built-in validation ensures your prompts receive the correct inputs every time.
  * **Reusability:** Define a prompt once and use it anywhere—in your Python code or directly from the CLI.
  * **Clarity:** A clear, human-readable format for prompts that anyone on your team can understand.

## ✨ Features

  - 📝 **Declarative & Structured:** Define prompts in simple `YAML` files with powerful **Jinja2** templating.
  - 🔍 **Built-in Validation:** Use **Pydantic** schemas to validate prompt inputs before they are ever sent to the LLM.
  - 🏗️ **Engine Agnostic:** A clean engine abstraction layer supports OpenAI, with Ollama and other local models on the way.
  - 💰 **Cost & Token Estimation:** Estimate token counts and potential costs *before* executing a prompt.
  - 🖥️ **Powerful CLI:** Render, run, and lint prompts directly from your terminal for rapid development and testing.
  - 🧪 **Fully Tested & Typed:** A comprehensive test suite and full type-hinting ensure reliability.

## 🚀 Quick Start

### 1. Installation

```
pip install promptkit-core
```

### 2. Define a Prompt

Create a file named `prompts/generate_greeting.yaml`:

```yaml
# prompts/generate_greeting.yaml
name: generate_greeting
description: "Generates a personalized and professional greeting."
template: |
  Hello {{ name }},

  Welcome to the team! We are excited to have a {{ role }} with your skills on board.

  Best,
  The PromptKit Team
input_schema:
  name: str
  role: str
```

### 3. Use in Python

```python
# main.py
from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.openai import OpenAIEngine

# Load prompt from YAML (assuming it's in a 'prompts' directory)
prompt = load_prompt("generate_greeting", prompt_dir="prompts")

# Configure engine
engine = OpenAIEngine(api_key="sk-...") # Or load from environment

# Run prompt with validated inputs
response = run_prompt(prompt, {"name": "Alice", "role": "Software Engineer"}, engine)
print(response)
```

### 4. Use the CLI

The CLI is perfect for quick tests, rendering, and validation.

```shell
# Set the directory where your prompts are stored (optional, can be passed as an argument)
export PROMPTKIT_PROMPT_DIR=./prompts

# Run the prompt directly from the terminal
promptkit run generate_greeting --key "sk-..." --name "Bob" --role "Data Scientist"

# Just render the template to see the output
promptkit render generate_greeting --name "Charlie" --role "Product Manager"

# Lint your YAML file to check for errors
promptkit lint generate_greeting
```

## 📚 Documentation

For detailed usage, advanced features, and API reference, please refer to the **[Official PromptKit Documentation](https://ochotzas.github.io/promptkit/)**.

## 🤝 Contributing

Contributions are welcome! Whether it's a bug report, a new feature, or a documentation improvement, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Install development dependencies: `pip install -e .[dev]`
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a Pull Request.

Please see the `CONTRIBUTING.md` file for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=https://github.com/ochotzas/promptkit/blob/main/LICENSE) file for details.