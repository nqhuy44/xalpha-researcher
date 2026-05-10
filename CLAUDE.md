# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**xalpha-researcher** — A multi-agent AI system for Vietnamese stock market analysis. Combines structured financial data (vnstock), Vietnamese-language news sentiment, an adversarial Bull-vs-Bear LLM debate, and risk-based position sizing. Runs as a set of independent Python services orchestrated via Docker Compose, plus a Next.js dashboard.

The system is **decision-support only** — never an automated trader. The Portfolio Agent issues advisory recommendations and must never execute trades.

## Common commands

Use `make` targets — they wrap the venv and PYTHONPATH correctly. Most Python invocations require `.venv/bin/python` and the project root on `PYTHONPATH`.

| Task                                                  | Command                                                      |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| Full setup (Python venv + Poetry deps + Next.js deps) | `make setup`                                                 |
| Install Python deps only                              | `make install` (Poetry)                                      |
| Lint                                                  | `make lint` (ruff, line-length 120, target py311)            |
| Format                                                | `make format`                                                |
| Run all tests                                         | `make test`                                                  |
| Run unit / integration only                           | `make test-unit` / `make test-integration`                   |
| Run a single test                                     | `.venv/bin/pytest tests/path/to/test_file.py::test_name -v`  |
| Start local infra (Postgres + Redis)                  | `make docker-up`                                             |
| Run main process (financial + news schedulers)        | `make run`                                                   |
| Run Telegram bot                                      | `make telegram-bot`                                          |
| Run financial worker only                             | `make financial-worker`                                      |
| Run news scheduler only                               | `make news-scheduler`                                        |
| Run AI engine API (legacy)                            | `make api`                                                   |
| Dashboard dev server                                  | `make dashboard-dev` (Next.js, port 3000)                    |
| Manual debate analysis                                | `make analyze TICKER=FPT ROUNDS=2`                           |
| 10-year historical bootstrap                          | `make bootstrap-financials`                                  |
| DB migrate                                            | `make migrate`                                               |
| New migration                                         | `make makemigrations m="description"`                        |
| Backups                                               | `make backup-full` (or `backup-news`, `backup-financial`, …) |
| Restore                                               | `make restore FILE=backups/full_*.sql.gz`                    |

`pytest` is configured with `asyncio_mode = "auto"` (see `pyproject.toml`) — async tests don't need a marker.

## Configuration

All settings flow through `src/config/settings.py` (Pydantic `BaseSettings`) and are read from `.env` using **double-underscore nesting**: `POSTGRES__HOST`, `LLM__PROVIDER`, `NEWS__SCHEDULE_HOURS`, etc. Add new config by extending one of the nested `BaseModel` classes (e.g. `GeminiSettings`, `NewsSettings`) — never read env vars directly.

Switch LLM provider with `LLM__PROVIDER` (gemini/openai/ollama/grok/deepseek/claude). Per-agent overrides go in `LLM__AGENT_PROVIDERS` as a dict.

## Architecture

The system is a **multi-process MAS**: one Docker image, several services with different `command:` overrides. They share Postgres (source of truth) and Redis (cache).

### Process services (`docker-compose.yaml`)

- `postgres` — `pgvector/pgvector:pg16`, volume `./pgdata`
- `redis` — `redis:8-alpine`, password-protected, volume `./redisdata`
- `migrator` — one-shot `alembic upgrade head`, blocks app services via `service_completed_successfully`
- `ai-engine` — FastAPI (`src.api.main`), proxied internally by the dashboard
- `dashboard` — Next.js (`./dashboard`), reads Postgres directly via Prisma + calls `ai-engine`
- `telegram-bot` — `src.interfaces.telegram.bot`
- `financial-worker` — `src.agents.financial.worker`, APScheduler-driven daily sync; auto-bootstraps 10y of data if Companies table is empty
- `news-scheduler` — `src.agents.news.scheduler`, RSS collection + LLM summarization on `NEWS__SCHEDULE_HOURS`

`src/main.py` runs the financial worker + news scheduler together in one process for local `make run`.

### Agent layer (`src/agents/`)

- **News** (`news/`) — RSS collector → HTML scrape (trafilatura) → LLM summarize → persist → Telegram report
- **Financial** (`financial/`) — vnstock client → EOD / profiles / financial reports / market intelligence (FX, gold, funds). Idempotent incremental sync uses benchmark-date comparison; dead/new tickers get **stub rows** to prevent retry loops
- **Analyst** (`analyst/`) — **LangGraph** debate. Graph in `analyst/graph.py`:
  - `data_aggregator` → fan-out to `bull` + `bear` (parallel) → `join` (increments round) → conditional loop on `max_rounds` → `judge` → conditional `referee` (only if confidence < 75 or retried verdict) → loop back to judge up to `max_judge_attempts`, else END
  - State lives in `analyst/state.py` (`AnalystState` Pydantic model)
- **Portfolio** (`portfolio/`) — LangGraph advisory pipeline (risk_manager → portfolio_manager). Advisory only, never trades. The graph is gated: after position fetch, `PortfolioEngine.process_signal` short-circuits unless the ticker is held OR the verdict is bullish (`Tiềm năng`/`Khả quan`) with `confidence_score ≥ PORTFOLIO_TRIGGER_CONFIDENCE` (70). Skipped runs return `None` — no `PortfolioSuggestion` row, which the dashboard treats as "no action recommended".
- **Signal** (`signal/`) — planned; CANSLIM + technical screening

### LLM abstraction (`src/services/llm/`)

`LLMProvider` ABC (`provider.py`) with concrete providers: gemini, openai, ollama, grok, deepseek, claude. Each implements `generate_text`, `generate_structured` (Pydantic schema output), and `summarize_batch` (news-optimized). The `LLMSettings.fast_model_role` / `deep_model_role` / `judge_model_role` map abstract tiers to provider models. Two-stage pattern: Flash-Lite for bulk extraction, Pro/Deep for synthesis.

### Data layer

- `src/data/sources/` — external connectors (vnstock, RSS, html scraper)
- `src/data/persistence/` — repositories (`financial_repo.py`, `news_repo.py`, `verdict_repo.py`) — go through these, not raw SQLAlchemy, in agent code
- `src/data/processing/` — transforms
- `src/db/models/` — SQLAlchemy ORM (analyst, finance, news, portfolio); Alembic migrations in `alembic/versions/`
- `src/db/session.py` — `async_session_factory` (asyncpg + SQLAlchemy 2.0 async)

### Dashboard (`dashboard/`)

Next.js 16 / React 19 / Tailwind 4 / Prisma. Server-side talks to Postgres via Prisma (`src/lib/prisma.ts`) and forwards heavy analysis to `ai-engine` via `INTERNAL_AI_URL`. Routes under `src/app/api/{analysis,auth,portfolio}` and pages under `src/app/analysis/`.

## Key conventions

- **Async everywhere.** DB, HTTP, LLM calls. `asyncio_mode=auto` for tests.
- **Repository pattern.** Agents call repositories, not ORM sessions directly.
- **Structured LLM output.** Use `generate_structured` with a Pydantic schema rather than parsing free text. The current debate schemas live in `src/agents/analyst/state.py` — `Argument(type, claim, evidence, acknowledged_counter, strength)` for openings and `Rebuttal(target_claim, flaw_type, counter_evidence, rebuttal_strength)` for rebuttals. Bull and Bear share the schemas; only the prompt differs. A more compact `fact / logic / score` triple is on the roadmap — see `docs/BACKLOG.md` T10.
- **One source of truth for debate transcripts.** `src/agents/analyst/utils/debate_formatting.py` (`format_argument`, `format_rebuttal`, `format_opponent_attacks`, `format_debate_transcript`) is used by Bull, Bear, Judge, and Referee. Do not re-implement transcript formatting inside a node.
- **Idempotent workers.** All sync jobs must be safe to re-run; `financial-worker` auto-detects empty DB and bootstraps.
- **3-layer risk gating** before any buy thesis surfaces: L1 data quality → L2 Bull/Bear debate (≥75% confidence) → L3 portfolio constraints. The Referee node enforces L2 when the Judge is uncertain.
- **Vietnamese market specifics.** Timezone `Asia/Ho_Chi_Minh` is set on every container. News and prompts are Vietnamese; `vnstock` rate-limits aggressively (`VNSTOCK__REQ_DELAY=3.0` default).

## Docs worth reading before non-trivial work

- `docs/ARCHITECTURE.md` — current vs planned components
- `docs/MULTI_AGENT_DESIGN.md` — debate optimization rationale (Gatekeeper, Referee, structured contracts)
- `docs/DEBATE_AGENT.md`, `docs/NEWS_AGENT.md`, `docs/PORTFOLIO_AGENT.md` — per-agent design
- `docs/DATABASE.md` — schema rationale
- `docs/RISK_CONTROL.md` — Kelly / VaR framework
- `docs/LLM_ABSTRACTION.md` — provider routing
