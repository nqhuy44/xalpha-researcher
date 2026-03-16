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
	@echo "🚀 Setting up Next.js Dashboard..."
	cd dashboard && npm install
	@echo "✅ Dashboard setup complete!"

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

api: ## Start the Portfolio UI API server (Legacy)
	.venv/bin/python -m src.api.main

dashboard-dev: ## Start Next.js Dashboard in development mode
	cd dashboard && npm run dev

dashboard-build: ## Build Next.js Dashboard for production
	cd dashboard && npm run build

# Manual news collection
collect-news: ## Collect news from sources and save to DB
	.venv/bin/python scripts/manage_news.py collect --hours 24 --persist

# Manual Debate Analysis
analyze: ## Run debate analysis for a ticker (e.g., make analyze TICKER=VNM ROUNDS=2)
	@if [ -z "$(TICKER)" ]; then echo "Error: TICKER is required (e.g., make analyze TICKER=FPT)"; exit 1; fi
	PYTHONPATH=. .venv/bin/python scripts/test_debate.py $(TICKER) $(ROUNDS)

telegram-bot: ## Start the Telegram Bot server
	.venv/bin/python -m src.interfaces.telegram.bot

bootstrap-financials: ## Run 10-year historical data bootstrap (Company profiles, EOD, Reports, Market Intelligence)
	.venv/bin/python scripts/bootstrap_financials.py

news-scheduler: ## Run News Scheduler standalone (collect + summarize + report)
	.venv/bin/python -m src.agents.news.scheduler

financial-worker: ## Run Financial Worker standalone (daily sync + market intelligence)
	.venv/bin/python -m src.agents.financial.worker

# ---------------------------------------------------------------------------
# Docker (Local Infrastructure)
# ---------------------------------------------------------------------------
docker-up: ## Start local infrastructure (PostgreSQL, Redis)
	docker compose up -d postgres redis

docker-down: ## Stop all containers
	docker compose down

# ---------------------------------------------------------------------------
# Docker Deployment (Production)
# ---------------------------------------------------------------------------
docker-build: ## Build the application Docker image
	docker compose build

deploy: ## Deploy ALL services (infra + app)
	docker compose up -d

deploy-infra: ## Deploy infrastructure only (PostgreSQL, Redis)
	docker compose up -d postgres redis

deploy-bot: ## Deploy Telegram Bot only
	docker compose up -d telegram-bot

deploy-dashboard: ## Deploy Next.js Dashboard only
	docker compose up -d dashboard

deploy-ai-engine: ## Deploy AI Engine only
	docker compose up -d ai-engine

deploy-financial: ## Deploy Financial Worker only
	docker compose up -d financial-worker

deploy-news: ## Deploy News Scheduler only
	docker compose up -d news-scheduler

deploy-workers: ## Deploy all workers (financial + news), no bot
	docker compose up -d financial-worker news-scheduler

docker-logs: ## View all service logs
	docker compose logs -f

# ---------------------------------------------------------------------------
# Database Migrations (Alembic)
# ---------------------------------------------------------------------------
migrate: ## Run Alembic migrations to apply schema changes
	.venv/bin/alembic upgrade head

makemigrations: ## Generate a new Alembic migration script (pass m="Message")
	.venv/bin/alembic revision --autogenerate -m "$(m)"

# ---------------------------------------------------------------------------
# Backup & Restore
# ---------------------------------------------------------------------------
backup-full: ## Backup ALL data (DB + Reports)
	./scripts/backup_db.sh full

backup-news: ## Backup news data only
	./scripts/backup_db.sh news

backup-financial: ## Backup financial data only
	./scripts/backup_db.sh financial

backup-debate: ## Backup debate verdicts only
	./scripts/backup_db.sh debate

backup-portfolio: ## Backup portfolio data only
	./scripts/backup_db.sh portfolio

backup-reports: ## Backup physical HTML reports only
	./scripts/backup_db.sh reports

restore: ## Restore data from a backup file (.sql.gz for DB, .tar.gz for Files)
	@if [ -z "$(FILE)" ]; then echo "Error: FILE is required (e.g., make restore FILE=backups/full_*.sql.gz)"; exit 1; fi
	./scripts/restore_db.sh $(FILE)

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