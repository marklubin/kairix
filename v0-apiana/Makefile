# Makefile for managing Ollama models with external system prompts

# Directories
SYSTEM_PROMPTS_DIR = ./system-prompts
MODELFILES_DIR = ./modelfiles
BASE_MODEL = ./mistralai_Mistral-7B-merged

# Default target
.PHONY: help
help:
	@echo "Apiana AI Development"
	@echo "===================="
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run unit tests only (default)"
	@echo "  make test-integ     - Run integration tests only"
	@echo "  make test-ui        - Run UI automation tests using Playwright"
	@echo "  make test-all       - Run all tests (unit + integration + ui)"
	@echo ""
	@echo "Ollama Model Management:"
	@echo "  make setup          - Create directories and sample prompts"
	@echo ""
	@echo "Generate Models:"
	@echo "  make coder          - Create coding assistant model"
	@echo "  make analyst        - Create data analyst model"
	@echo "  make writer         - Create technical writer model"
	@echo "  make all-models     - Create all predefined models"
	@echo ""
	@echo "Management:"
	@echo "  make list-prompts   - List available system prompts"
	@echo "  make list-models    - List created Ollama models"
	@echo "  make clean          - Remove generated Modelfiles"

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

.PHONY: test-comprehensive
test-comprehensive:
	@echo "Running comprehensive test suite with environment checks..."
	@uv run python run_all_tests.py

.PHONY: setup
setup:
	@echo "Setting up directories and sample prompts..."
	@mkdir -p $(SYSTEM_PROMPTS_DIR) $(MODELFILES_DIR)
	@python3 scripts/modelfile_generator.py --create-samples
	@echo "✓ Setup complete"

.PHONY: coder
coder: setup
	@echo "Generating coding assistant model..."
	@python3 scripts/modelfile_generator.py \
		--model-name mistral-coder \
		--base-model $(BASE_MODEL) \
		--system-prompt coding-assistant.txt \
		--temperature 0.3 \
		--max-tokens 1000
	@echo "To create: ollama create mistral-coder -f $(MODELFILES_DIR)/mistral-coder.Modelfile"

.PHONY: analyst
analyst: setup
	@echo "Generating data analyst model..."
	@python3 scripts/modelfile_generator.py \
		--model-name mistral-analyst \
		--base-model $(BASE_MODEL) \
		--system-prompt data-scientist.txt \
		--temperature 0.4 \
		--max-tokens 800

.PHONY: writer
writer: setup
	@echo "Generating technical writer model..."
	@python3 scripts/modelfile_generator.py \
		--model-name mistral-writer \
		--base-model $(BASE_MODEL) \
		--system-prompt creative-writer.txt \
		--temperature 0.8 \
		--max-tokens 1200

.PHONY: all-models
all-models: coder analyst writer
	@echo ""
	@echo "All Modelfiles generated. To create all models:"
	@echo "make install-all"

.PHONY: install-all
install-all:
	@echo "Creating all Ollama models..."
	@if [ -f $(MODELFILES_DIR)/mistral-coder.Modelfile ]; then \
		ollama create mistral-coder -f $(MODELFILES_DIR)/mistral-coder.Modelfile; \
	fi
	@if [ -f $(MODELFILES_DIR)/mistral-analyst.Modelfile ]; then \
		ollama create mistral-analyst -f $(MODELFILES_DIR)/mistral-analyst.Modelfile; \
	fi
	@if [ -f $(MODELFILES_DIR)/mistral-writer.Modelfile ]; then \
		ollama create mistral-writer -f $(MODELFILES_DIR)/mistral-writer.Modelfile; \
	fi

.PHONY: list-prompts
list-prompts:
	@echo "Available system prompts:"
	@ls -la $(SYSTEM_PROMPTS_DIR)/*.txt 2>/dev/null || echo "No prompts found. Run 'make setup' first."

.PHONY: list-models
list-models:
	@echo "Created Ollama models:"
	@ollama list | grep mistral || echo "No mistral models found"

.PHONY: clean
clean:
	@echo "Cleaning generated Modelfiles..."
	@rm -f $(MODELFILES_DIR)/*.Modelfile
	@echo "✓ Cleanup complete"