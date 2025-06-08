# Makefile for kairix-server module

# Module-specific variables
MODULE_NAME := kairix-server
MODULE_PATH := $(shell pwd)

# Include common targets
include ../make/common.mk

# Module-specific targets can be added here
.PHONY: serve
serve: ## Start the server
	@echo "🚀 Starting $(MODULE_NAME)..."
	@uv run python -m kairix_server

# Override the help target to use module-help
.PHONY: help
help: module-help

.DEFAULT_GOAL := help