.PHONY: help install install-dev test test-cov lint format type-check clean build docs serve-docs clean-docs bench codemod pricing-refresh pricing-check example cli-help cli-test lock all

COVERAGE_FLOOR ?= 80

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	@command -v pre-commit >/dev/null 2>&1 && pre-commit install || echo "⚠️  pre-commit not found after install"

test: ## Run tests
	@python -c "import pytest" 2>/dev/null || { echo "⚠️  pytest not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	@python -c "import pytest" 2>/dev/null || { echo "⚠️  pytest not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m pytest tests/ -v --cov=promptkit --cov-report=html --cov-report=term --cov-fail-under=$(COVERAGE_FLOOR)

lint: ## Run linting and format check
	@python -c "import ruff" 2>/dev/null || { echo "⚠️  ruff not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m ruff check promptkit/ tests/
	python -m ruff format --check promptkit/ tests/

format: ## Format code and apply safe lint fixes
	@python -c "import ruff" 2>/dev/null || { echo "⚠️  ruff not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m ruff check promptkit/ tests/ --fix
	python -m ruff format promptkit/ tests/

type-check: ## Run type checking
	@python -c "import mypy" 2>/dev/null || { echo "⚠️  mypy not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m mypy

check-deps: ## Check if development dependencies are installed
	@echo "🔍 Checking development dependencies..."
	@python -c "import ruff" 2>/dev/null && echo "✅ ruff installed" || echo "❌ ruff not found"
	@python -c "import mypy" 2>/dev/null && echo "✅ mypy installed" || echo "❌ mypy not found"
	@python -c "import pytest" 2>/dev/null && echo "✅ pytest installed" || echo "❌ pytest not found"
	@command -v pre-commit >/dev/null 2>&1 && echo "✅ pre-commit installed" || echo "❌ pre-commit not found"
	@echo ""
	@echo "💡 If any tools are missing, run: make install-dev"

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf site/
	rm -rf .benchmarks/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lock: ## Refresh uv.lock from pyproject.toml
	@command -v uv >/dev/null 2>&1 || { echo "⚠️  uv not found. See https://docs.astral.sh/uv/"; exit 1; }
	uv lock

build: ## Build package
	@python -c "import build" 2>/dev/null || { echo "⚠️  build not found. Run 'pip install build' or 'make install-dev' to install it."; exit 1; }
	python -m build

docs: ## Build the documentation site
	@command -v mkdocs >/dev/null 2>&1 || { echo "⚠️  mkdocs not found. Run 'make install-dev'."; exit 1; }
	mkdocs build --strict

clean-docs: ## Remove the built documentation site
	rm -rf site/

serve-docs: ## Serve the documentation with live reload
	@command -v mkdocs >/dev/null 2>&1 || { echo "⚠️  mkdocs not found. Run 'make install-dev'."; exit 1; }
	mkdocs serve

pricing-refresh: ## Update the vendored model pricing snapshot
	python scripts/refresh_pricing.py

pricing-check: ## Fail if the pricing snapshot is out of date
	python scripts/refresh_pricing.py --check

bench: ## Run the benchmarks
	python -m pytest benchmarks/ --benchmark-columns=mean,ops --benchmark-sort=name

codemod: ## Preview the 1.0 codemod against a target (TARGET=path)
	python -m promptkit.codemod $(or $(TARGET),.)

example: ## Run example script
	python examples/example.py

cli-help: ## Show CLI help
	python -m promptkit.cli.main --help

cli-test: ## Smoke-test the CLI
	python -m promptkit.cli.main engines
	python -m promptkit.cli.main list examples
	python -m promptkit.cli.main lint examples
	python -m promptkit.cli.main info examples/support_reply.yaml
	python -m promptkit.cli.main render examples/greet_user.yaml --set name="Test User"
	python -m promptkit.cli.main cost examples/greet_user.yaml --set name="Test User"

all: format lint type-check test ## Run all quality checks
