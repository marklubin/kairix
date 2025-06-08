# Module runner - allows running any target in any module from root
# Usage: make module-run MODULE=kairix-offline TARGET=test

.PHONY: module-run
module-run: ## Run a target in a specific module
	@if [ -z "$(MODULE)" ]; then \
		echo "Error: MODULE not specified. Usage: make module-run MODULE=<module-name> TARGET=<target>"; \
		exit 1; \
	fi
	@if [ -z "$(TARGET)" ]; then \
		echo "Error: TARGET not specified. Usage: make module-run MODULE=<module-name> TARGET=<target>"; \
		exit 1; \
	fi
	@if [ ! -d "$(MODULE)" ]; then \
		echo "Error: Module $(MODULE) not found"; \
		exit 1; \
	fi
	@echo "Running '$(TARGET)' in $(MODULE)..."
	@$(MAKE) -C $(MODULE) $(TARGET)

# Convenience targets for common operations across all modules
.PHONY: test-all-modules
test-all-modules: ## Run tests in all modules
	@for module in kairix-core kairix-offline kairix-server; do \
		echo "════════════════════════════════════════"; \
		echo "Testing $$module..."; \
		echo "────────────────────────────────────────"; \
		$(MAKE) -C $$module test || true; \
	done

.PHONY: lint-all-modules
lint-all-modules: ## Run linting in all modules
	@for module in kairix-core kairix-offline kairix-server; do \
		echo "════════════════════════════════════════"; \
		echo "Linting $$module..."; \
		echo "────────────────────────────────────────"; \
		$(MAKE) -C $$module lint || true; \
	done

.PHONY: build-all-modules
build-all-modules: ## Build all modules
	@for module in kairix-core kairix-offline kairix-server; do \
		echo "════════════════════════════════════════"; \
		echo "Building $$module..."; \
		echo "────────────────────────────────────────"; \
		$(MAKE) -C $$module build || true; \
	done