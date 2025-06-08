# Include module runner for cross-module operations
include make/module-runner.mk

.PHONY: install
install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

.PHONY: check
check: ## Run code quality tools (ruff + mypy).
	@echo "🚀 Running all code quality checks"
	@uv run python scripts/check.py

.PHONY: fix
fix: ## Auto-fix code style issues with ruff.
	@echo "🔧 Fixing code style issues"
	@uv run python scripts/fix.py

.PHONY: check-old
check-old: ## Run code quality tools (old version).
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "🧪 Running unit tests..."
	@cd kairix-offline && uv run pytest -m unit -v

.PHONY: test-integration
test-integration: ## Run integration tests only (requires Docker)
	@echo "🔗 Running integration tests..."
	@cd kairix-offline && uv run pytest -m integration -v

.PHONY: test-all
test-all: ## Run all tests in all projects
	@echo "🧪 Running all tests..."
	@echo "──────────────────────────────────────"
	@echo "Testing kairix-offline..."
	@cd kairix-offline && uv run pytest -v
	@echo "──────────────────────────────────────"
	@echo "Testing kairix-core..."
	@cd kairix-core && uv run pytest -v 2>/dev/null || echo "No tests in kairix-core"
	@echo "──────────────────────────────────────"
	@echo "Testing kairix-server..."
	@cd kairix-server && uv run pytest -v 2>/dev/null || echo "No tests in kairix-server"

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: build-all
build-all: ## Build all projects
	@echo "🏗️  Building all projects..."
	@echo "──────────────────────────────────────"
	@echo "Building kairix (root)..."
	@uvx --from build pyproject-build --installer uv
	@echo "──────────────────────────────────────"
	@echo "Building kairix-core..."
	@cd kairix-core && uvx --from build pyproject-build --installer uv
	@echo "──────────────────────────────────────"
	@echo "Building kairix-offline..."
	@cd kairix-offline && uvx --from build pyproject-build --installer uv
	@echo "──────────────────────────────────────"
	@echo "Building kairix-server..."
	@cd kairix-server && uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing."
	@uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@uv run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@uv run mkdocs serve

.PHONY: all
all: ## Run all checks, tests, and builds
	@echo "🚀 Running complete build pipeline..."
	@echo "════════════════════════════════════════"
	@echo "Step 1/4: Code quality checks"
	@echo "────────────────────────────────────────"
	@$(MAKE) check
	@echo ""
	@echo "Step 2/4: Unit tests"
	@echo "────────────────────────────────────────"
	@$(MAKE) test-unit
	@echo ""
	@echo "Step 3/4: Integration tests"
	@echo "────────────────────────────────────────"
	@$(MAKE) test-integration
	@echo ""
	@echo "Step 4/4: Building all projects"
	@echo "────────────────────────────────────────"
	@$(MAKE) build-all
	@echo ""
	@echo "✅ All checks, tests, and builds completed successfully!"

.PHONY: clean-all
clean-all: ## Clean everything (venv, builds, caches) and start from scratch
	@echo "🧹 Performing complete cleanup..."
	@echo "════════════════════════════════════════"
	@echo "Removing virtual environments..."
	@rm -rf .venv
	@rm -rf kairix-core/.venv
	@rm -rf kairix-offline/.venv
	@rm -rf kairix-server/.venv
	@echo "✓ Virtual environments removed"
	@echo ""
	@echo "Removing build artifacts..."
	@rm -rf dist
	@rm -rf kairix-core/dist
	@rm -rf kairix-offline/dist
	@rm -rf kairix-server/dist
	@rm -rf build
	@rm -rf kairix-core/build
	@rm -rf kairix-offline/build
	@rm -rf kairix-server/build
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Build artifacts removed"
	@echo ""
	@echo "Removing Python caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✓ Python caches removed"
	@echo ""
	@echo "Removing lock files..."
	@rm -f uv.lock
	@rm -f kairix-core/uv.lock
	@rm -f kairix-offline/uv.lock
	@rm -f kairix-server/uv.lock
	@echo "✓ Lock files removed"
	@echo ""
	@echo "✅ Complete cleanup finished!"
	@echo ""
	@echo "To start fresh, run:"
	@echo "  make install"
	@echo "  make all"

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
