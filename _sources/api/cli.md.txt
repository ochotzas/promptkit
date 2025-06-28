# CLI API Reference

Complete reference for PromptKit's command-line interface and CLI utilities.

## Overview

PromptKit provides a comprehensive command-line interface for prompt management, execution, and development workflows. The CLI is designed to integrate seamlessly with development pipelines and supports both interactive and batch operations.

## Installation and Setup

The CLI is automatically available after installing PromptKit:

```bash
pip install promptkit-core
promptkit --help
```

### Environment Configuration

Set up environment variables for common configurations:

```bash
# OpenAI Configuration
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4"

# Azure OpenAI Configuration
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="your-deployment"

# Anthropic Configuration
export ANTHROPIC_API_KEY="your-key"

# Default prompt directory
export PROMPTKIT_PROMPT_DIR="./prompts"
```

## Main Command: `promptkit`

### Global Options

```bash
promptkit [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]

Global Options:
  --config PATH              Configuration file path [default: ~/.promptkit/config.yaml]
  --prompt-dir PATH          Directory containing prompt files [default: ./prompts]
  --engine TEXT              Engine to use [default: openai]
  --verbose, -v              Enable verbose logging
  --quiet, -q                Suppress output except errors
  --format [json|yaml|text]  Output format [default: text]
  --help                     Show help message
  --version                  Show version information
```

## Core Commands

### `run` - Execute Prompts

Execute a prompt with input data.

```bash
promptkit run PROMPT_NAME [OPTIONS]

Options:
  --input PATH               JSON/YAML file with input data
  --input-json TEXT          Input data as JSON string
  --var KEY=VALUE            Set individual input variables (multiple allowed)
  --output PATH              Save output to file
  --stream                   Enable streaming output
  --temperature FLOAT        Sampling temperature [0.0-2.0]
  --max-tokens INTEGER       Maximum tokens to generate
  --top-p FLOAT             Nucleus sampling parameter [0.0-1.0]
  --stop TEXT               Stop sequence (multiple allowed)
  --cost-estimate           Show cost estimate before execution
  --dry-run                 Validate inputs without execution

Examples:
  # Run with input file
  promptkit run summarize --input data.json

  # Run with inline variables
  promptkit run greet --var name="John" --var age=30

  # Run with streaming
  promptkit run write_story --var topic="space" --stream

  # Estimate cost first
  promptkit run analyze_data --input large_dataset.json --cost-estimate
```

### `list` - List Available Prompts

List and search prompts in the prompt directory.

```bash
promptkit list [OPTIONS]

Options:
  --search TEXT              Search prompts by name or description
  --tag TEXT                 Filter by tag (multiple allowed)
  --format [table|json|yaml] Output format [default: table]
  --show-details             Show detailed information
  --show-schema              Include input schema information

Examples:
  # List all prompts
  promptkit list

  # Search prompts
  promptkit list --search "analysis"

  # Filter by tags
  promptkit list --tag data --tag report

  # Detailed view with schemas
  promptkit list --show-details --show-schema
```

### `validate` - Validate Prompts

Validate prompt files and input data.

```bash
promptkit validate [PROMPT_NAME] [OPTIONS]

Options:
  --input PATH               Validate specific input file
  --input-json TEXT          Validate JSON input string
  --schema-only              Only validate schema, not template
  --fix                      Attempt to fix common issues
  --strict                   Enable strict validation mode

Examples:
  # Validate all prompts
  promptkit validate

  # Validate specific prompt
  promptkit validate user_profile

  # Validate with input data
  promptkit validate user_profile --input test_data.json

  # Schema validation only
  promptkit validate user_profile --schema-only
```

### `create` - Create New Prompts

Create new prompt files from templates or interactively.

```bash
promptkit create PROMPT_NAME [OPTIONS]

Options:
  --template TEXT            Template to use [basic|chat|analysis|creative]
  --interactive, -i          Interactive prompt creation
  --description TEXT         Prompt description
  --input-schema PATH        Input schema file (JSON/YAML)
  --output PATH              Output file path
  --tags TEXT                Comma-separated tags
  --overwrite                Overwrite existing prompt

Examples:
  # Interactive creation
  promptkit create my_prompt --interactive

  # Create from template
  promptkit create analysis_prompt --template analysis

  # Create with metadata
  promptkit create report_gen --description "Generate reports" --tags "report,business"
```

### `edit` - Edit Prompts

Edit existing prompts with validation.

```bash
promptkit edit PROMPT_NAME [OPTIONS]

Options:
  --editor TEXT              Editor to use [default: $EDITOR]
  --validate                 Validate after editing
  --backup                   Create backup before editing
  --field TEXT               Edit specific field [template|schema|description]

Examples:
  # Edit prompt in default editor
  promptkit edit user_profile

  # Edit specific field
  promptkit edit user_profile --field template

  # Edit with auto-validation
  promptkit edit user_profile --validate
```

### `test` - Test Prompts

Run test suites for prompts.

```bash
promptkit test [PROMPT_NAME] [OPTIONS]

Options:
  --test-file PATH           Test configuration file
  --input-dir PATH           Directory with test input files
  --output-dir PATH          Directory to save test outputs
  --baseline PATH            Baseline results for comparison
  --coverage                 Generate test coverage report
  --parallel INTEGER         Number of parallel test workers
  --timeout INTEGER          Test timeout in seconds

Examples:
  # Test all prompts
  promptkit test

  # Test specific prompt
  promptkit test summarize --test-file tests/summarize_tests.yaml

  # Run with baseline comparison
  promptkit test --baseline results/baseline.json
```

### `init` - Initialize Project

Initialize a new PromptKit project.

```bash
promptkit init [PROJECT_NAME] [OPTIONS]

Options:
  --template TEXT            Project template [basic|advanced|enterprise]
  --engine TEXT              Default engine to configure
  --git                      Initialize git repository
  --examples                 Include example prompts
  --config                   Create configuration files

Examples:
  # Basic initialization
  promptkit init my_project

  # Advanced project with examples
  promptkit init ai_app --template advanced --examples --git
```

## Engine Management

### `engine` - Engine Operations

Manage and configure engines.

```bash
promptkit engine COMMAND [OPTIONS]

Commands:
  list                       List available engines
  info ENGINE               Show engine information
  configure ENGINE          Configure engine settings
  test ENGINE               Test engine connectivity
  benchmark ENGINE          Benchmark engine performance

Examples:
  # List available engines
  promptkit engine list

  # Show engine info
  promptkit engine info openai

  # Configure engine
  promptkit engine configure azure_openai

  # Test connectivity
  promptkit engine test anthropic
```

## Batch Operations

### `batch` - Batch Processing

Execute prompts in batch mode.

```bash
promptkit batch [OPTIONS]

Options:
  --jobs PATH                Batch job configuration file
  --input-dir PATH           Directory with input files
  --output-dir PATH          Directory for output files
  --workers INTEGER          Number of parallel workers [default: 4]
  --resume                   Resume interrupted batch job
  --progress                 Show progress bar
  --summary                  Generate summary report

Examples:
  # Run batch job
  promptkit batch --jobs batch_config.yaml --workers 8

  # Process directory of inputs
  promptkit batch --input-dir inputs/ --output-dir outputs/

  # Resume interrupted job
  promptkit batch --jobs batch_config.yaml --resume
```

### Batch Configuration File

```yaml
# batch_config.yaml
name: "Document Analysis Batch"
description: "Analyze multiple documents"

prompts:
  - name: "analyze_document"
    inputs_dir: "inputs/documents"
    output_dir: "outputs/analysis"
    input_pattern: "*.txt"

  - name: "summarize_document"
    inputs_dir: "inputs/documents"
    output_dir: "outputs/summaries"
    input_pattern: "*.txt"

engine:
  type: "openai"
  model: "gpt-4"
  temperature: 0.3

settings:
  parallel_workers: 4
  retry_attempts: 3
  timeout: 60
```

## Development Commands

### `dev` - Development Tools

Development and debugging utilities.

```bash
promptkit dev COMMAND [OPTIONS]

Commands:
  watch                      Watch prompts for changes and auto-validate
  serve                      Start development server with API
  debug PROMPT_NAME          Debug prompt execution
  profile PROMPT_NAME        Profile prompt performance
  export                     Export prompts to different formats

Examples:
  # Watch for changes
  promptkit dev watch --auto-test

  # Start dev server
  promptkit dev serve --port 8000

  # Debug prompt
  promptkit dev debug complex_analysis --verbose

  # Profile performance
  promptkit dev profile batch_process --iterations 100
```

### `export` - Export Prompts

Export prompts to various formats.

```bash
promptkit export [OPTIONS]

Options:
  --format [openai|anthropic|json|yaml]  Export format
  --output PATH              Output file or directory
  --prompts TEXT             Specific prompts to export (comma-separated)
  --include-metadata         Include metadata in export
  --compress                 Compress output

Examples:
  # Export to OpenAI format
  promptkit export --format openai --output openai_prompts.json

  # Export specific prompts
  promptkit export --prompts "prompt1,prompt2" --format yaml

  # Export with compression
  promptkit export --compress --output prompts.tar.gz
```

## Configuration Management

### `config` - Configuration Operations

Manage PromptKit configuration.

```bash
promptkit config COMMAND [OPTIONS]

Commands:
  show                       Show current configuration
  set KEY VALUE              Set configuration value
  unset KEY                  Remove configuration value
  reset                      Reset to default configuration
  validate                   Validate configuration file

Examples:
  # Show configuration
  promptkit config show

  # Set default engine
  promptkit config set default_engine anthropic

  # Set API key
  promptkit config set engines.openai.api_key sk-...

  # Validate config
  promptkit config validate
```

### Configuration File Format

```yaml
# ~/.promptkit/config.yaml
default_engine: openai
prompt_directory: ./prompts
output_format: text

engines:
  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    temperature: 0.7
    max_tokens: 1000

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-2
    max_tokens_to_sample: 1000

  azure_openai:
    api_key: ${AZURE_OPENAI_API_KEY}
    endpoint: ${AZURE_OPENAI_ENDPOINT}
    deployment_name: ${AZURE_OPENAI_DEPLOYMENT}

logging:
  level: INFO
  file: ~/.promptkit/logs/promptkit.log

cache:
  enabled: true
  ttl: 3600
  directory: ~/.promptkit/cache

development:
  auto_validate: true
  auto_reload: true
  debug_mode: false
```

## Shell Integration

### Shell Completion

Enable shell completion for better CLI experience:

```bash
# Bash
eval "$(_PROMPTKIT_COMPLETE=bash_source promptkit)"

# Zsh
eval "$(_PROMPTKIT_COMPLETE=zsh_source promptkit)"

# Fish
eval (env _PROMPTKIT_COMPLETE=fish_source promptkit)
```

### Aliases and Functions

Useful shell aliases:

```bash
# ~/.bashrc or ~/.zshrc
alias pk="promptkit"
alias pkrun="promptkit run"
alias pklist="promptkit list"
alias pktest="promptkit test"

# Function for quick prompt execution
pkexec() {
    promptkit run "$1" --var "${@:2}"
}

# Function for interactive prompt creation
pknew() {
    promptkit create "$1" --interactive
}
```

## Output Formats

### JSON Output

```bash
promptkit run summarize --input data.json --format json
```

```json
{
  "prompt_name": "summarize",
  "input_data": {...},
  "response": "Generated summary text...",
  "metadata": {
    "engine": "openai",
    "model": "gpt-4",
    "tokens_used": 150,
    "cost": 0.003,
    "duration": 2.5
  }
}
```

### YAML Output

```bash
promptkit list --format yaml
```

```yaml
prompts:
  - name: summarize
    description: Summarize text content
    tags: [text, analysis]
    schema:
      type: object
      properties:
        content: {type: string}
        max_length: {type: integer}
```

## Error Handling

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Validation error
- `3`: Engine error
- `4`: Configuration error
- `5`: File not found error

### Common Error Messages

```bash
# Missing prompt
Error: Prompt 'unknown_prompt' not found in ./prompts

# Invalid input
Error: Input validation failed:
  - name: field required
  - age: must be a positive integer

# Engine error
Error: OpenAI API error (429): Rate limit exceeded

# Configuration error
Error: No API key configured for engine 'openai'
```

## Advanced Usage

### Pipeline Integration

```bash
# CI/CD pipeline example
#!/bin/bash
set -e

# Validate all prompts
promptkit validate

# Run test suite
promptkit test --coverage

# Generate documentation
promptkit export --format json --output dist/prompts.json

# Deploy prompts
promptkit batch --jobs deployment.yaml
```

### Custom Scripts

```bash
#!/bin/bash
# process_documents.sh

INPUT_DIR="$1"
OUTPUT_DIR="$2"

for file in "$INPUT_DIR"/*.txt; do
    filename=$(basename "$file" .txt)
    echo "Processing $filename..."

    promptkit run analyze_document \
        --var content="$(cat "$file")" \
        --output "$OUTPUT_DIR/${filename}_analysis.txt"
done
```

This comprehensive CLI reference covers all aspects of using PromptKit from the command line, enabling efficient prompt development and deployment workflows.
