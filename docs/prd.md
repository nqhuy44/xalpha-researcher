# Product Requirements Document (PRD)

| Field | Value |
|---|---|
| **Project Name** | xalpha-researcher — Personalized AI Agent System for Vietnamese Stock Market Analysis |
| **Version** | v1.0.0 |
| **Last Updated** | 2026-02-24 |
| **Primary Audience** | Personal, Non-Commercial Use |
| **Author** | @nqhuy |

---

## 1. Executive Summary

The financial market in Vietnam is highly volatile, driven heavily by retail investor sentiment (~80% of trading volume), and is on a transition path toward emerging market status by 2026-2027. This project builds a **personalized, autonomous Multi-Agent System (MAS)** to analyze the Vietnamese stock market.

By combining structured financial data, Natural Language Processing (NLP) for market sentiment, and quantitative risk models, the system identifies "smart money" signals and manages personal capital efficiently while eliminating emotional trading biases.

### 1.1. Problem Statement

- Retail investors in Vietnam lack access to **institutional-grade analysis tools**.
- Information asymmetry and **herd mentality** cause irrational price swings.
- Manual analysis across multiple domains (finance, geopolitics, law, macro) is **time-prohibitive**.
- Emotional biases (**confirmation bias**, **FOMO**, **loss aversion**) lead to poor decision-making.

### 1.2. Proposed Solution

A multi-agent AI system that autonomously:
1. Ingests and validates financial data from structured APIs.
2. Analyzes multi-domain news sentiment in Vietnamese.
3. Screens equities using quantitative and fundamental methods (CANSLIM).
4. Stress-tests every investment hypothesis via adversarial debate (Bull vs Bear).
5. Calculates optimal position sizing using mathematical risk models.
6. Delivers actionable alerts via Telegram and a secure dashboard.

---

## 2. Core Objectives

| # | Objective | Description |
|---|---|---|
| O1 | **Data Integrity** | Prioritize clean, structured digital data from financial APIs (SSI, TCBS, Vietstock) over error-prone OCR. |
| O2 | **Sentiment & Macro Tracking** | Anticipate crowd euphoria/panic by analyzing local forums, news, and global geopolitical events. |
| O3 | **Adversarial Decision Making** | Implement Bull vs. Bear debate to stress-test hypotheses and eliminate confirmation bias. |
| O4 | **Automated Risk Management** | Utilize Kelly Criterion, VaR, and dynamic position sizing tailored for frontier market constraints. |
| O5 | **Explainability** | Provide transparent SHAP-based breakdowns of every AI recommendation. |

---

## 3. System Architecture & Multi-Agent Framework

The core reasoning engine is built on a **decentralized Multi-Agent architecture** orchestrated via **LangGraph**, enabling state management, backtracking, and human-in-the-loop approvals.

### 3.1. News Agent (Sentiment Sensor)

| Aspect | Detail |
|---|---|
| **Function** | Extracts sentiment from news, forums, social media across multiple domains: finance, wars, geopolitics, economics, law & regulations, technology. |
| **NLP Model** | PhoBERT — fine-tuned for Vietnamese financial terminology. |
| **Output** | Sentiment score from -1 (very negative) to +1 (very positive). |
| **Capabilities** | Tone shift detection in corporate reports, news deduplication to prevent "echo bias", multi-source monitoring (Cafef, Vietstock, VnExpress, F319, Telegram groups). |
| **Data Sources** | RSS feeds, financial news APIs, forum scrapers. |

### 3.2. Signal Agent (Quantitative Screener)

| Aspect | Detail |
|---|---|
| **Function** | Filters equities based on CANSLIM methodology and technical indicators. |
| **CANSLIM Criteria** | C: Q-o-Q EPS growth > 20-25%, A: 3-5yr annual earnings growth, N: New products/management, S: Volume-based supply/demand, L: RS Rating > 80-90th percentile, I: Institutional sponsorship, M: Market direction. |
| **Technical Indicators** | RSI, MACD, Bollinger Bands, Moving Averages, Volume analysis. |
| **ML Models** | XGBoost (structured data), Random Forest/CNN (chart pattern recognition). |
| **Output** | Scored buy/sell signals with confidence levels. |

### 3.3. Debate Agent (Risk Control via Adversarial Reasoning)

| Aspect | Detail |
|---|---|
| **Function** | Spawns Bull and Bear personas to adversarially debate every "Buy" signal. |
| **Bull Arguments** | Growth catalysts, favorable economic cycles, undervaluation metrics (low P/E), positive technical setups. |
| **Bear Arguments** | Hidden risks: bad debt, inflation pressure, geopolitical risks, corporate governance issues, energy infrastructure bottlenecks. |
| **Output** | Synthesized multi-dimensional report with weighted risk assessment. |
| **LLM** | Gemini 2.5 Pro (complex reasoning, 2M token context). |

### 3.4. Portfolio Agent (Execution & Capital Management)

| Aspect | Detail |
|---|---|
| **Function** | Final execution layer and long-term asset management. |
| **Risk Models** | Kelly Criterion (Half-Kelly for frontier markets), Value at Risk (VaR), SHAP explainability. |
| **Market-Specific** | T+2.5 settlement cycle monitoring, margin ratio tracking at brokerages, mass margin call early warning. |
| **Position Sizing** | Liquidity-adjusted, dynamic sizing based on portfolio VaR limits. |
| **Output** | Capital allocation recommendations, portfolio rebalancing signals. |

### 3.5. Agent Orchestration Flow

```
News Agent → Signal Agent → Debate Agent → Portfolio Agent → User Alert
     ↑              ↑              ↑                ↑
     └──────────── LangGraph State Management ──────┘
                  (backtrack, iterate, human-in-the-loop)
```

1. **News Agent** detects significant events (e.g., major export contract).
2. **Signal Agent** analyzes financial impact using historical data + CANSLIM scoring.
3. **Debate Agent** conducts Bull/Bear adversarial debate on risks.
4. **Portfolio Agent** calculates optimal allocation via Kelly + VaR.
5. **System** delivers concise recommendation via Telegram Bot + Dashboard.

---

## 4. Technical Stack & Platform Infrastructure

### 4.1. Data Layer & Databases

| Layer | Technology | Purpose |
|---|---|---|
| **Primary Ingestion** | `vnstock` library, SSI/TCBS APIs | Clean JSON financial data (20+ years of balance sheets, income statements, cash flow). |
| **Caching & Real-time** | Redis 8.x | Real-time stock prices, user sessions, rapid vector search (<100ms latency). |
| **Primary & Vector DB** | PostgreSQL 16 + pgvector | Single source of truth for relational data + embeddings for RAG. |
| **Object Storage** | S3-compatible | Archive original PDF reports, agent inference logs for model fine-tuning. |

> **Data Quality Gate**: Any stock missing ≥4 out of 12 key financial indicators is flagged "Poor Data" and rejected from analysis.

### 4.2. LLM Engine — Model Routing Strategy

The system uses **Model Routing** to balance TCO with performance:

| Model | Context Window | Input Cost/1M | Output Cost/1M | Assigned Tasks |
|---|---|---|---|---|
| Gemini 2.5 Pro | 2,000,000 tokens | $1.25 | $10.00 | Complex reasoning, financial statement analysis, Debate Agent |
| Gemini 2.5 Flash | 1,000,000 tokens | $0.30 | $2.50 | Real-time agent tasks, orchestration |
| Gemini 2.5 Flash-Lite | 1,000,000 tokens | $0.10 | $0.40 | News sentiment classification, raw data extraction |

**Cost Optimization Strategies**:
- **Context Caching**: Static legal/historical data cached to reduce input costs by up to 90%.
- **Batch Processing**: End-of-day analytics processed in batch mode (50% cost reduction).
- **Grounding with Google Search**: Mitigates hallucinations by cross-referencing real-world data.

### 4.3. ML/NLP Stack

| Component | Technology | Purpose |
|---|---|---|
| **Sentiment Analysis** | PhoBERT (fine-tuned) | Vietnamese financial sentiment classification |
| **Structured Data ML** | XGBoost | Non-linear financial pattern recognition |
| **Chart Patterns** | Random Forest / CNN | Technical chart pattern recognition |
| **Explainability** | SHAP | Transparent decision breakdown |

### 4.4. Frontend & Deployment

| Component | Technology | Rationale |
|---|---|---|
| **Dashboard** | React + Vite | Sub-2s server start, efficient HMR, lightweight bundles (~42KB). |
| **Charting** | TradingView Lightweight Charts | Plot AI signals on real-time candlestick data. |
| **Auth** | JWT | Protect personal financial data. |
| **Containerization** | Docker + Docker Compose | Reproducible local dev and deployment. |
| **Orchestration** | LangGraph | Agent state management, backtracking, human-in-the-loop. |

### 4.5. Core Python Dependencies

| Category | Libraries |
|---|---|
| **Data** | `vnstock`, `pandas`, `numpy`, `httpx`, `feedparser` |
| **NLP/ML** | `transformers`, `torch`, `xgboost`, `scikit-learn`, `shap` |
| **LLM** | `google-genai`, `langchain`, `langgraph` |
| **DB** | `asyncpg`, `sqlalchemy`, `redis`, `pgvector` |
| **API/Bot** | `fastapi`, `uvicorn`, `python-telegram-bot` |
| **DevOps** | `pydantic-settings`, `structlog`, `pytest` |

---

## 5. Quantitative Risk Management Models

### 5.1. Kelly Criterion

Calculates the optimal fraction of capital to allocate per trade:

$$f^* = \frac{\mu - r}{\sigma^2}$$

Where:
- $f^*$ = optimal capital ratio
- $\mu$ = expected return
- $r$ = risk-free rate
- $\sigma^2$ = variance of returns

> [!IMPORTANT]
> **Half-Kelly Strategy**: To mitigate extreme volatility of the Vietnamese frontier market, the system always applies 50% of the calculated Kelly fraction. If Kelly suggests 20%, the system allocates **10%**.

### 5.2. Value at Risk (VaR)

Calculates maximum expected loss over a specific timeframe at **95% confidence interval**.

$$VaR_{\alpha} = \mu - z_{\alpha} \cdot \sigma$$

### 5.3. SHAP Explainability

Every recommendation includes a transparent breakdown. Example:
- 40% weight: Foreign capital inflows surge
- 30% weight: EPS beats expectations
- 20% weight: Favorable technical setup
- 10% weight: Positive sector rotation

---

## 6. User Interfaces

### 6.1. Telegram Bot (Execution & Alerts)

- **Conversational Interface**: Natural language queries (e.g., "What is the biggest risk to my portfolio?").
- **Tiered Alerts**:

| Level | Type | Trigger |
|---|---|---|
| **Level 1** | 🔴 Urgent | Risk threshold violations, margin call warnings |
| **Level 2** | 🟡 Tactical | Buy/Sell signals from Signal Agent with Bull/Bear consensus |
| **Level 3** | 🔵 Informational | EOD summaries: proprietary trading flows, foreign fund activity |

### 6.2. Secure Dashboard (Deep Analysis)

- Real-time charts with technical indicators and AI-generated buy/sell signals.
- Full **Explainability Report** including raw Bull/Bear debate output.
- **Macro Scenario Simulation**: "What if GDP grows 10%?", "What if market upgrade succeeds?"

---

## 7. Data Sources

| Category | Sources | Format |
|---|---|---|
| **Stock Market** | SSI, TCBS, VCI (via `vnstock`) | JSON API |
| **Financial Reports** | Vietstock, FiinGroup, FiinTrade | JSON API, structured data |
| **Macro Indicators** | Vietdata, General Statistics Office | GDP, CPI, FDI, interest rates, M2, FX rates (20yr history) |
| **News & Sentiment** | Cafef, VnExpress, Vietstock News | RSS feeds, API |
| **Forums & Social** | F319, Telegram groups, Zalo | Web scraping, social listening |
| **Legal/Regulatory** | Government Gazette, SBV announcements | RSS, structured feeds |
| **Corporate Events** | FiinTrade, Vietstock | Capital increases, insider trading, subsidiary lists |

---

## 8. Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Latency** | Real-time data ingestion: <100ms (Redis cache layer). Dashboard load: <2s. |
| **Availability** | System designed for personal use; 99% uptime on local/cloud infra. |
| **Scalability** | Single-user system; horizontal scaling not required for MVP. |
| **Security** | JWT auth, `.env` secrets management, no hardcoded credentials. |
| **Data Retention** | Raw financial data: indefinite. Agent logs: 1 year. Embeddings: refreshed quarterly. |
| **Logging** | Structured logging (`structlog`), levels: DEBUG/INFO/WARN/ERROR. |
| **Observability** | Health check endpoints for all services. Graceful shutdown on SIGTERM. |
| **Idempotency** | All scripts and data pipelines safe to run multiple times. |
| **Cost** | Target <$50/month LLM API costs via model routing + caching + batching. |

---

## 9. Phased Roadmap

### Phase 0 — Foundation (Current)
- [x] Project research and PRD documentation.
- [ ] Folder structure and skeleton setup.
- [ ] Config files, environment templates, Docker Compose.
- [ ] Mandatory documentation (`ARCHITECTURE.md`, `TECH_STACK.md`, etc.).

### Phase 1 — Data Pipeline (MVP)
- [ ] Financial data ingestion via `vnstock` (SSI/TCBS).
- [ ] News/RSS feed collection (multi-domain).
- [ ] PostgreSQL + pgvector setup with initial schema.
- [ ] Redis caching layer.
- [ ] Data quality gate implementation.

### Phase 2 — Core Agents
- [ ] News Agent: PhoBERT sentiment analysis pipeline.
- [ ] Signal Agent: CANSLIM scoring + technical indicators.
- [ ] LangGraph orchestration setup.
- [ ] Basic Telegram Bot for alerts.

### Phase 3 — Advanced Intelligence
- [ ] Debate Agent: Bull/Bear adversarial reasoning.
- [ ] Portfolio Agent: Kelly Criterion + VaR position sizing.
- [ ] SHAP explainability integration.
- [ ] Model routing (Gemini Pro / Flash / Flash-Lite).

### Phase 4 — User Interfaces
- [ ] Secure Dashboard (React + Vite + TradingView Charts).
- [ ] Full Telegram Bot with conversational AI.
- [ ] Macro scenario simulation.
- [ ] Context caching and batch processing optimization.

### Phase 5 — Refinement
- [ ] Walk-forward analysis (continuous model retraining).
- [ ] Vietnamese legal/regulatory compliance checks.
- [ ] Performance optimization and cost reduction.
- [ ] Comprehensive test suite.

---

## 10. Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Signal Accuracy** | >60% win rate on Buy signals over 6-month rolling window | Backtesting + forward testing |
| **Sentiment Accuracy** | >80% classification accuracy (PhoBERT) | Benchmark against labeled Vietnamese financial news dataset |
| **Alert Latency** | <5 minutes from event detection to Telegram notification | End-to-end pipeline monitoring |
| **LLM Cost** | <$50/month average | API billing dashboard |
| **Data Coverage** | >90% of HOSE/HNX listed stocks with complete financial data | Data quality gate reports |
| **Explainability** | 100% of recommendations include SHAP breakdown | Automated check in Portfolio Agent |

---

## 11. Constraints & Assumptions

### Constraints
- **Single-user system**: No multi-tenancy, no user management beyond owner.
- **API rate limits**: vnstock, SSI, TCBS APIs have rate limits; must implement backoff.
- **T+2.5 settlement**: Vietnamese market settlement cycle affects real-time execution logic.
- **Language**: All NLP must handle Vietnamese with financial domain terminology.
- **Budget**: Personal project; infrastructure costs must remain minimal.

### Assumptions
- Financial APIs (vnstock, SSI, TCBS) remain available and stable.
- Gemini API pricing and availability remain consistent.
- PhoBERT or equivalent Vietnamese NLP model remains open-source.
- User has basic infrastructure (local machine or low-cost cloud VM).

---

## 12. Glossary

| Term | Definition |
|---|---|
| **CANSLIM** | Investment methodology by William O'Neil focusing on 7 criteria (Current earnings, Annual earnings, New products, Supply/demand, Leader/laggard, Institutional sponsorship, Market direction). |
| **Kelly Criterion** | Mathematical formula for optimal bet sizing to maximize long-term capital growth. |
| **VaR** | Value at Risk — statistical measure of maximum expected loss at a given confidence level. |
| **SHAP** | Shapley Additive Explanations — method for explaining ML model predictions. |
| **PhoBERT** | Pre-trained language model specifically designed for Vietnamese NLP tasks. |
| **LangGraph** | Framework for building stateful, multi-agent AI applications with graph-based orchestration. |
| **RAG** | Retrieval-Augmented Generation — technique to ground LLM responses in factual data. |
| **pgvector** | PostgreSQL extension for vector similarity search, enabling embedding storage. |
| **MAS** | Multi-Agent System — architecture where multiple autonomous agents collaborate. |
| **T+2.5** | Vietnamese stock market settlement cycle (trade date + 2.5 business days). |
| **EOD** | End of Day — refers to daily market close data and analytics. |
| **TCO** | Total Cost of Ownership — complete cost analysis including API, infra, and maintenance. |
| **HMR** | Hot Module Replacement — development feature for instant UI updates without full reload. |
| **RS Rating** | Relative Strength Rating — measures a stock's price performance vs. all other stocks. |