# Makefile for managing Ollama models with external system prompts

# Testing targets
.PHONY: test
test:
	@echo "Running unit tests..."
	@uv run pytest

.PHONY: test-integ
test-integ:
	@echo "Running integration tests..."
	@uv run pytest -v -k "integration" --ignore=scripts/

.PHONY: test-ui
test-ui:
	@echo "Running UI automation tests..."
	@echo "Installing Playwright browsers if needed..."
	@uv run playwright install chromium --with-deps
	@echo "Starting UI automation tests..."
	@uv run pytest tests/ui_automation/ -v -m "ui_automation" -k ""

.PHONY: test-all
test-all:
	@echo "Running all tests..."
	@uv run pytest -v --ignore=scripts/ -k ""

.PHONY: start-gradio
start-gradio:
	@docker compose up -d
	@uv run ruff check --fix
	@uv run mem-ui

.PHONY: install
install:
	@mkdir -p neo4j
	@uv sync
	@uv run ruff check --fix

.PHONY: create-env
create-env:
	@cp default.env .env

.PHONY: lint
lint:
	@uv run ruff check --fix

.PHONY: clean
clean:
	@echo "Cleaning generated Modelfiles..."
	@rm -rf .venv dist
	@echo "✓ Cleanup complete"
