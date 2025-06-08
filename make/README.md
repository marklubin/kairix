# Shared Make Scripts for Kairix

This directory contains shared Makefile components used across all Kairix modules.

## Structure

- `common.mk` - Common targets shared by all modules (test, lint, build, etc.)
- `module-runner.mk` - Utilities for running targets in modules from the root directory

## How it works

Each module (kairix-core, kairix-offline, kairix-server) has its own Makefile that:
1. Sets module-specific variables (MODULE_NAME)
2. Includes the shared `common.mk` file
3. Can override or extend common targets
4. Can add module-specific targets

## Usage

### From within a module directory:
```bash
cd kairix-offline
make test          # Run all tests
make test-unit     # Run unit tests
make lint          # Run linting
make build         # Build the package
make help          # Show all available targets
```

### From the root directory:
```bash
# Run any target in any module
make module-run MODULE=kairix-offline TARGET=test
make module-run MODULE=kairix-core TARGET=build

# Run common operations across all modules
make test-all-modules    # Test all modules
make lint-all-modules    # Lint all modules
make build-all-modules   # Build all modules
```

## Adding a new module

1. Create a Makefile in your module directory:
```makefile
# Makefile for my-module

# Module-specific variables
MODULE_NAME := my-module
MODULE_PATH := $(shell pwd)

# Include common targets
include ../make/common.mk

# Add module-specific targets here
.PHONY: my-custom-target
my-custom-target: ## Description of my target
	@echo "Running custom target..."

# Override help to use module-help
.PHONY: help
help: module-help

.DEFAULT_GOAL := help
```

2. The module automatically gets all common targets from `common.mk`

## Customizing shared targets

To customize a shared target in a specific module, simply redefine it in the module's Makefile:

```makefile
# Override the test target with custom behavior
.PHONY: test
test: ## Run tests with custom settings
	@echo "Running custom test configuration..."
	@uv run pytest -v --special-flag
```

## Benefits

1. **DRY (Don't Repeat Yourself)**: Common targets defined once
2. **Consistency**: All modules have the same interface
3. **Maintainability**: Update common behavior in one place
4. **Flexibility**: Modules can override or extend as needed
5. **Discoverability**: `make help` works in every module