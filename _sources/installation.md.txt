# Installation

## Requirements

PromptKit requires Python 3.10 or higher.

## Install from PyPI

```bash
pip install promptkit-core
```

## Development Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/ochotzas/promptkit.git
cd promptkit
pip install -e '.[dev]'
```

## Verify Installation

```bash
promptkit --version
```

Or in Python:

```python
import promptkit
print(promptkit.__version__)
```

## Engine Setup

### OpenAI

Set your API key:

```bash
export OPENAI_API_KEY="sk-your-api-key"
```

### Ollama

Install and start Ollama:

```bash
# See https://ollama.ai for installation
ollama serve
ollama pull llama2
```
