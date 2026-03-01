# Tech Stack — xalpha-researcher

## Language & Runtime

| Tool | Version | Rationale |
|---|---|---|
| Python | 3.11+ | Async support, match group syntax, ML ecosystem maturity |
| Poetry | Latest | Deterministic dependency resolution, lockfile |

## LLM & AI

| Tool | Version | Rationale |
|---|---|---|
| Google Gemini 2.5 Pro | Latest | 2M token context, complex reasoning, Grounding with Google Search |
| Google Gemini 2.5 Flash | Latest | Low-latency real-time agent tasks |
| Google Gemini 2.5 Flash-Lite | Latest | Cost-optimized high-volume extraction ($0.10/1M input) |
| LangGraph | ^0.3 | Graph-based agent orchestration, state management, human-in-the-loop |
| LangChain | ^0.3 | LLM abstraction layer, tool integration |

## NLP & Machine Learning

| Tool | Version | Rationale |
|---|---|---|
| PhoBERT | Latest | Pre-trained Vietnamese language model, >81% sentiment accuracy |
| Hugging Face Transformers | ^4.40 | Model loading and inference pipeline |
| PyTorch | ^2.0 | Deep learning backend for PhoBERT |
| XGBoost | ^2.0 | Non-linear financial pattern recognition |
| scikit-learn | ^1.5 | Classical ML, Random Forest, preprocessing |
| SHAP | ^0.46 | Model explainability (Shapley values) |

## Data & Databases

| Tool | Version | Rationale |
|---|---|---|
| PostgreSQL | 16 | Relational SSOT, mature ecosystem, JSON support |
| pgvector | ^0.3 | Vector similarity search for RAG embeddings |
| Redis | 8.x | Sub-100ms caching, real-time data, in-memory vector search |
| SQLAlchemy | ^2.0 | Async ORM with type safety |
| asyncpg | ^0.30 | High-performance async PostgreSQL driver |

## Data Sources

| Tool | Version | Rationale |
|---|---|---|
| vnstock | ^3.0 | Clean JSON financial data from SSI/TCBS (20yr history) |
| feedparser | ^6.0 | RSS feed parsing for news ingestion |
| httpx | ^0.28 | Async HTTP client for API integrations |
| pandas | ^2.0 | Data manipulation and analysis |
| numpy | ^2.0 | Numerical computation |

## API & User Interfaces

| Tool | Version | Rationale |
|---|---|---|
| FastAPI | ^0.115 | High-performance async API framework |
| Uvicorn | ^0.34 | ASGI server for FastAPI |
| python-telegram-bot | ^21.0 | Telegram Bot API integration |
| React + Vite | Latest | Sub-2s dev server, lightweight bundles (~42KB) |
| TradingView Lightweight Charts | Latest | Real-time candlestick charts with AI signal overlay |

## Security

| Tool | Version | Rationale |
|---|---|---|
| python-jose | ^3.3 | JWT token generation and validation |
| Pydantic Settings | ^2.0 | Type-safe environment variable management |

## DevOps & Quality

| Tool | Version | Rationale |
|---|---|---|
| Docker + Compose | Latest | Containerized local dev (PostgreSQL, Redis) |
| Ruff | ^0.9 | Fast Python linter + formatter (replaces flake8+black+isort) |
| pytest | ^8.0 | Test framework with async support |
| structlog | ^24.0 | Structured JSON logging |
