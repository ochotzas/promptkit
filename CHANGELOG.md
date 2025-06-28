# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of PromptKit
- YAML-based prompt definitions with Jinja2 templating
- Input validation using Pydantic schemas
- Engine abstraction supporting OpenAI and Ollama
- Token estimation and cost calculation
- CLI interface with commands: run, render, lint, info, cost
- Comprehensive test suite with pytest
- Example prompts and usage scripts
- Full documentation and development guide

### Features
- **Core Components:**
  - `Prompt` class for structured prompt management
  - `Schema` validation with Pydantic v2
  - `Compiler` for Jinja2 template rendering
  - `Loader` for YAML prompt files
  - `Runner` for orchestrating prompt execution

- **Engines:**
  - OpenAI API integration (sync/async)
  - Ollama local model support
  - Extensible base engine architecture

- **Utilities:**
  - Token counting with tiktoken
  - Cost estimation for different models
  - Unified logging system

- **CLI:**
  - Interactive prompt execution
  - Template rendering and validation
  - Cost estimation
  - Rich formatted output

### Technical Details
- Python 3.8+ support
- Full type hints throughout
- Comprehensive error handling
- Production-ready architecture
- Extensible plugin system

## [0.1.0] - 2025-06-28

### Added
- Initial project structure
- Core functionality implementation
- Basic documentation
- Test suite setup
