.PHONY: help test lint format check install-dev install-hooks

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test:  ## Run pytest test suite
	cd app && python -m pytest tests/ -v --tb=short

lint:  ## Run linting checks (ruff + black --check + isort --check)
	ruff check app/
	black --check --line-length=120 app/
	isort --check-only --profile=black --line-length=120 app/

format:  ## Auto-format code (black + isort + ruff --fix)
	black --line-length=120 app/
	isort --profile=black --line-length=120 app/
	ruff check --fix app/

check:  ## Run all checks (lint + test)
	@echo "Running linting checks..."
	@$(MAKE) lint
	@echo "\nRunning tests..."
	@$(MAKE) test
	@echo "\n✓ All checks passed!"

install-dev:  ## Install development dependencies
	pip install -r app/requirements.txt -r app/requirements-dev.txt

install-hooks:  ## Install pre-commit hooks
	pre-commit install
	@echo "✓ Pre-commit hooks installed. Run 'pre-commit run --all-files' to test."

# Default target
.DEFAULT_GOAL := help
