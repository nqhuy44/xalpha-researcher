.PHONY: help setup install lint format test run clean docker-up docker-down

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup & Install
# ---------------------------------------------------------------------------
setup: ## Full project setup (venv + deps + infra)
	@echo "🚀 Setting up xalpha-researcher..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install poetry
	.venv/bin/poetry install
	@echo "📋 Copy .env.example to .env and fill in your values"
	@test -f .env || cp .env.example .env
	@echo "✅ Setup complete! Activate venv: source .venv/bin/activate"

install: ## Install dependencies only
	poetry install

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------
lint: ## Run linters (ruff)
	ruff check src/ tests/

format: ## Auto-format code (ruff)
	ruff format src/ tests/

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test: ## Run test suite
	pytest tests/ -v --tb=short

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests only
	pytest tests/integration/ -v --tb=short

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
run: ## Run the main application
	.venv/bin/python -m src.main

# Manual news collection
collect-news: ## Collect news from sources and save to DB
	.venv/bin/python scripts/manage_news.py collect --hours 24 --persist

telegram-bot: ## Start the Telegram Bot server
	.venv/bin/python -m src.interfaces.telegram.bot

# ---------------------------------------------------------------------------
# Docker (Local Infrastructure)
# ---------------------------------------------------------------------------
docker-up: ## Start local infrastructure (PostgreSQL, Redis)
	docker compose up -d

docker-down: ## Stop local infrastructure
	docker compose down

# ---------------------------------------------------------------------------
# Database Migrations (Alembic)
# ---------------------------------------------------------------------------
migrate: ## Run Alembic migrations to apply schema changes
	.venv/bin/alembic upgrade head

makemigrations: ## Generate a new Alembic migration script (pass m="Message")
	.venv/bin/alembic revision --autogenerate -m "$(m)"

docker-logs: ## View infrastructure logs
	docker compose logs -f

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/ htmlcov/ .coverage
	@echo "🧹 Cleaned!"

# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------
# release with argument version
release: ## Build and release the application
	@echo "🚀 Releasing $(VERSION)..."
	docker build -t nqh44/xalpha-researcher:$(VERSION) .
	docker push nqh44/xalpha-researcher:$(VERSION)
	@echo "✅ Release complete!"