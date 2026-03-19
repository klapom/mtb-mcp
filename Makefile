.PHONY: help install dev run test test-unit test-integration lint lint-fix format type-check quality clean docker-up docker-down docker-logs

help:  ## Show this help message
	@echo "MTB MCP Server — Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation & Setup
# ============================================================================

install:  ## Install dependencies
	pip install --upgrade pip
	pip install poetry
	poetry install

dev:  ## Install with development dependencies
	poetry install --with dev
	poetry run pre-commit install

# ============================================================================
# Development
# ============================================================================

run:  ## Run MCP server (stdio transport)
	poetry run python -m mtb_mcp

# ============================================================================
# Testing
# ============================================================================

test:  ## Run all tests
	poetry run pytest

test-unit:  ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	poetry run pytest tests/integration/ -v

test-cov:  ## Run tests with coverage report
	poetry run pytest --cov=src/mtb_mcp --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

# ============================================================================
# Code Quality
# ============================================================================

lint:  ## Run linter (Ruff check)
	poetry run ruff check src/ tests/

lint-fix:  ## Run linter with auto-fix
	poetry run ruff check src/ tests/ --fix

format:  ## Format code (Ruff format)
	poetry run ruff format src/ tests/

type-check:  ## Run type checker (MyPy)
	poetry run mypy src/

quality:  ## Run all quality checks
	$(MAKE) lint
	$(MAKE) type-check

# ============================================================================
# Docker (BRouter + SearXNG)
# ============================================================================

docker-up:  ## Start BRouter + SearXNG
	docker compose up -d
	@echo "Waiting for services..."
	@sleep 3
	docker compose ps

docker-down:  ## Stop all Docker services
	docker compose down

docker-restart:  ## Restart all Docker services
	docker compose restart

docker-logs:  ## Show Docker logs
	docker compose logs -f

docker-ps:  ## Show Docker service status
	docker compose ps

docker-clean:  ## Remove containers and volumes
	docker compose down -v

# ============================================================================
# Cleanup
# ============================================================================

clean:  ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ coverage.xml .coverage dist/ build/
	@echo "Cleaned temporary files"

# ============================================================================
# Default
# ============================================================================

.DEFAULT_GOAL := help
