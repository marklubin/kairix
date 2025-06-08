# Common make targets for all kairix modules
# This file is included by each module's Makefile

.PHONY: test
test: ## Run all tests
	@echo "🧪 Running tests for $(MODULE_NAME)..."
	@uv run pytest -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests for $(MODULE_NAME)..."
	@uv run pytest -m unit -v

.PHONY: test-integration
test-integration: ## Run integration tests only (requires Docker)
	@echo "🔗 Running integration tests for $(MODULE_NAME)..."
	@uv run pytest -m integration -v

.PHONY: lint
lint: ## Run linting with ruff
	@echo "🔍 Linting $(MODULE_NAME)..."
	@uv run ruff check src/

.PHONY: format
format: ## Format code with ruff
	@echo "📐 Formatting $(MODULE_NAME)..."
	@uv run ruff format src/
	@uv run ruff check --fix src/

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	@echo "🔎 Type checking $(MODULE_NAME)..."
	@uv run mypy src/

.PHONY: check
check: lint typecheck ## Run all code quality checks
	@echo "✅ All checks passed for $(MODULE_NAME)!"

.PHONY: build
build: clean ## Build the package
	@echo "🏗️  Building $(MODULE_NAME)..."
	@uvx --from build pyproject-build --installer uv

.PHONY: clean
clean: ## Clean build artifacts and caches
	@echo "🧹 Cleaning $(MODULE_NAME)..."
	@rm -rf dist build *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true

.PHONY: install
install: ## Install dependencies
	@echo "📦 Installing dependencies for $(MODULE_NAME)..."
	@uv sync

.PHONY: dev
dev: install ## Set up development environment
	@echo "🛠️  Setting up development environment for $(MODULE_NAME)..."
	@uv run pre-commit install 2>/dev/null || true

# Help target
.PHONY: module-help
module-help:
	@echo "Available targets for $(MODULE_NAME):"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'