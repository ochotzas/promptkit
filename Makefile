.PHONY: help install install-dev test test-cov lint format type-check clean build docs serve-docs

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
	python -m pytest promptkit/tests/ -v

test-cov: ## Run tests with coverage
	@python -c "import pytest" 2>/dev/null || { echo "⚠️  pytest not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m pytest promptkit/tests/ -v --cov=promptkit --cov-report=html --cov-report=term

lint: ## Run linting
	@python -c "import ruff" 2>/dev/null || { echo "⚠️  ruff not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	@python -c "import black" 2>/dev/null || { echo "⚠️  black not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m ruff check promptkit/
	python -m black --check promptkit/

format: ## Format code
	@python -c "import black" 2>/dev/null || { echo "⚠️  black not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	@python -c "import isort" 2>/dev/null || { echo "⚠️  isort not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	@python -c "import ruff" 2>/dev/null || { echo "⚠️  ruff not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m black promptkit/
	python -m isort promptkit/
	python -m ruff check promptkit/ --fix

type-check: ## Run type checking
	@python -c "import mypy" 2>/dev/null || { echo "⚠️  mypy not found. Run 'make install-dev' to install development dependencies."; exit 1; }
	python -m mypy promptkit/

check-deps: ## Check if development dependencies are installed
	@echo "🔍 Checking development dependencies..."
	@python -c "import black" 2>/dev/null && echo "✅ black installed" || echo "❌ black not found"
	@python -c "import isort" 2>/dev/null && echo "✅ isort installed" || echo "❌ isort not found"
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
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build package
	python -m build

docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not implemented yet"

serve-docs: ## Serve documentation locally (placeholder)
	@echo "Documentation serving not implemented yet"

example: ## Run example script
	python examples/example.py

cli-help: ## Show CLI help
	python -m promptkit.cli.main --help

cli-test: ## Test CLI commands
	python -m promptkit.cli.main info examples/greet_user.yaml
	python -m promptkit.cli.main render examples/greet_user.yaml --vars '{"name": "Test User"}'
	python -m promptkit.cli.main cost examples/greet_user.yaml --name "Test User"

all: format lint type-check test ## Run all quality checks
