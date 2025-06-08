# Makefile for kairix-offline module

# Module-specific variables
MODULE_NAME := kairix-offline
MODULE_PATH := $(shell pwd)

# Include common targets
include ../make/common.mk

# Module-specific targets (override or extend common ones)

.PHONY: test-ui
test-ui: ## Run UI automation tests
	@echo "Running UI automation tests..."
	@echo "Installing Playwright browsers if needed..."
	@uv run playwright install firefox --with-deps
	@echo "Starting UI automation tests..."
	@uv run pytest tests/ui -v -m "ui"

.PHONY: test-ui-headless
test-ui-headless: ## Run UI tests in headless mode
	@uv run pytest tests/ui -m ui --ui-headless -v

.PHONY: test-ui-debug
test-ui-debug: ## Run UI tests in debug mode
	PWDEBUG=1 uv run pytest tests/ui -m ui -s

.PHONY: start-gradio
start-gradio: ## Start Gradio UI with docker services
	@docker compose up -d
	@uv run ruff check --fix
	@uv run mem-ui

.PHONY: create-env
create-env: ## Create .env file from template
	@cp default.env .env
	@echo "Created .env file from default.env"

# Override the help target to use module-help
.PHONY: help
help: module-help

.DEFAULT_GOAL := help