# Installation

## Requirements

PromptKit requires Python 3.8 or higher.

## Install from PyPI

The recommended way to install PromptKit is via pip:

```bash
pip install promptkit-core
```

## Development Installation

For development, clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/ochotzas/promptkit.git
cd promptkit
pip install -e .[dev]
```

## Verify Installation

You can verify your installation by running:

```bash
promptkit --version
```

Or in Python:

```python
import promptkit
print(promptkit.__version__)
```

## Optional Dependencies

### OpenAI

To use OpenAI models, you'll need to set your API key:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### Ollama

To use local models with Ollama, install and start Ollama:

```bash
# Install Ollama (see https://ollama.ai for platform-specific instructions)
ollama serve

# Pull a model
ollama pull llama2
```

## Next Steps

Once installed, check out the [Quick Start Guide](tutorials/quickstart.md) to begin using PromptKit.
