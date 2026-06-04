.PHONY: help install clean test test-fast lint lint-fix format format-check \
        typecheck check ci agent-build bump bump-patch bump-minor bump-major

.DEFAULT_GOAL := help

UV     := uv
RUFF   := ruff
PYTEST := pytest

AGENT_SPEC   := dooservice-agent.spec
AGENT_BINARY := dist/dooservice-agent

GREEN  := \033[0;32m
YELLOW := \033[1;33m
CYAN   := \033[0;36m
RED    := \033[0;31m
NC     := \033[0m

CURRENT_VERSION = $(shell grep '^version' pyproject.toml | sed 's/version = "//;s/"//')

help:
	@echo "$(GREEN)dooservice agent — Development Commands$(NC)\n"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
	    {printf "  $(YELLOW)%-18s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "\n$(CYAN)Current version: $(CURRENT_VERSION)$(NC)"

install: ## Install dependencies and pre-commit hooks
	$(UV) sync
	$(UV) run pre-commit install

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

test: ## Run all tests
	$(UV) run $(PYTEST) -v --tb=short || [ $$? -eq 5 ]

test-fast: ## Run tests, stop on first failure
	$(UV) run $(PYTEST) -x --tb=short || [ $$? -eq 5 ]

lint: ## Run ruff linter
	$(UV) run $(RUFF) check src/

lint-fix: ## Auto-fix lint issues
	$(UV) run $(RUFF) check --fix src/

format: ## Format code
	$(UV) run $(RUFF) format src/

format-check: ## Check formatting without changes
	$(UV) run $(RUFF) format --check src/

typecheck: ## Run basedpyright
	$(UV) run basedpyright src/

check: lint format-check ## Lint + format check

ci: install check test ## Full CI pipeline locally

agent-build: ## Compile standalone binary via PyInstaller
	$(UV) run pyinstaller --clean --noconfirm $(AGENT_SPEC)
	@echo "$(GREEN)Binary: $(AGENT_BINARY)$(NC)"

bump-patch: ## Bump patch version (1.0.0 → 1.0.1) and release
	@CURRENT=$(CURRENT_VERSION) ; \
	 MAJOR=$$(echo $$CURRENT | cut -d. -f1) ; \
	 MINOR=$$(echo $$CURRENT | cut -d. -f2) ; \
	 PATCH=$$(echo $$CURRENT | cut -d. -f3) ; \
	 NEW="$$MAJOR.$$MINOR.$$((PATCH+1))" ; \
	 echo "$(CYAN)Bumping $$CURRENT → $$NEW$(NC)" ; \
	 $(MAKE) bump VERSION=$$NEW

bump-minor: ## Bump minor version (1.0.0 → 1.1.0) and release
	@CURRENT=$(CURRENT_VERSION) ; \
	 MAJOR=$$(echo $$CURRENT | cut -d. -f1) ; \
	 MINOR=$$(echo $$CURRENT | cut -d. -f2) ; \
	 NEW="$$MAJOR.$$((MINOR+1)).0" ; \
	 echo "$(CYAN)Bumping $$CURRENT → $$NEW$(NC)" ; \
	 $(MAKE) bump VERSION=$$NEW

bump-major: ## Bump major version (1.0.0 → 2.0.0) and release
	@CURRENT=$(CURRENT_VERSION) ; \
	 MAJOR=$$(echo $$CURRENT | cut -d. -f1) ; \
	 NEW="$$((MAJOR+1)).0.0" ; \
	 echo "$(CYAN)Bumping $$CURRENT → $$NEW$(NC)" ; \
	 $(MAKE) bump VERSION=$$NEW

bump: ## Release a specific version: make bump VERSION=1.2.0
	@[ "$(VERSION)" != "" ] || { echo "$(RED)Set VERSION: make bump VERSION=1.2.0$(NC)"; exit 1; }
	@grep -q "## \[$(VERSION)\]" CHANGELOG.md || { \
	    echo "$(RED)Add ## [$(VERSION)] section to CHANGELOG.md before releasing$(NC)"; exit 1; }
	sed -i 's/^version = .*/version = "$(VERSION)"/' pyproject.toml
	git add pyproject.toml
	git diff --cached --quiet || git commit -m "chore: bump agent to $(VERSION)"
	git tag $(VERSION)
	git push origin HEAD
	git push origin $(VERSION)
	@echo "$(GREEN)✓ Agent v$(VERSION) tagged — CI will build and publish the binary$(NC)"
