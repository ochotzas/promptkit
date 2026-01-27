# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-01-27

### Changed
- Simplified and cleaned up all docstrings
- Rewrote documentation to match actual implementation
- Removed references to non-existent features

### Fixed
- Documentation now accurately reflects the API
- Removed non-existent `prompt_dir` parameter from examples
- Fixed CLI command documentation

## [0.1.0] - 2025-06-28

### Added
- YAML-based prompt definitions with Jinja2 templating
- Input validation using Pydantic schemas
- OpenAI engine with sync/async support
- Ollama engine for local models
- Token estimation and cost calculation
- CLI commands: `run`, `render`, `lint`, `info`, `cost`
- Example prompts and usage scripts

### Features
- `Prompt` class for structured prompt management
- `load_prompt()` and `save_prompt()` for YAML files
- `run_prompt()` and `run_prompt_async()` for execution
- Extensible `BaseEngine` architecture

### Technical
- Python 3.10+ required
- Full type hints
- Pydantic v2 for validation
- httpx for HTTP requests
