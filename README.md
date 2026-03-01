# xalpha-researcher

> Personalized AI Agent System for Vietnamese Stock Market Analysis

A multi-agent AI system that combines structured financial data, NLP sentiment analysis, and quantitative risk models to analyze the Vietnamese stock market. Built for personal, non-commercial use.

## Architecture

The system uses 4 specialized AI agents orchestrated via **LangGraph**:

| Agent | Role | Key Technology |
|---|---|---|
| **News Agent** | Sentiment extraction from multi-domain Vietnamese news | PhoBERT |
| **Signal Agent** | Quantitative stock screening (CANSLIM + technicals) | XGBoost, RSI, MACD |
| **Debate Agent** | Adversarial Bull vs Bear reasoning | Gemini 2.5 Pro |
| **Portfolio Agent** | Risk management & position sizing | Kelly Criterion, VaR |

## Tech Stack

- **Language**: Python 3.11+
- **LLM**: Google Gemini 2.5 (Pro / Flash / Flash-Lite)
- **Orchestration**: LangGraph
- **Database**: PostgreSQL 16 + pgvector, Redis 8
- **NLP**: PhoBERT (Vietnamese sentiment)
- **ML**: XGBoost, scikit-learn, SHAP
- **Interfaces**: Telegram Bot, React + Vite Dashboard
- **Data**: vnstock, RSS feeds, financial APIs

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url> && cd xalpha-researcher
make setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start infrastructure
make docker-up

# 4. Run
make run
```

## Project Structure

```
src/
├── agents/          # Multi-agent system (news, signal, debate, portfolio)
├── config/          # Pydantic settings (env-based)
├── data/            # Data ingestion & processing
├── db/              # PostgreSQL + Redis layer
├── interfaces/      # Telegram bot, web dashboard
├── llm/             # Gemini integration & model routing
├── models/          # ML/NLP models (sentiment, quantitative)
└── risk/            # Kelly Criterion, VaR, position sizing
```

## Documentation

- [Product Requirements (PRD)](docs/prd.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Tech Stack](docs/TECH_STACK.md)
- [Data Flows](docs/FLOWS.md)
- [Database Design](docs/DATABASE.md)

## License

Personal, non-commercial use only.
