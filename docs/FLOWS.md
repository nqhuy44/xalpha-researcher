# Data Flows — xalpha-researcher

## 1. Agent Orchestration Flow

Main pipeline from data ingestion to user alert delivery.

```mermaid
sequenceDiagram
    participant DS as Data Sources
    participant DQ as Data Quality Gate
    participant NA as News Agent
    participant SA as Signal Agent
    participant DA as Debate Agent
    participant PA as Portfolio Agent
    participant TG as Telegram Bot
    participant DB as Dashboard

    DS->>DQ: Raw financial data + news
    DQ->>DQ: Validate (≥8/12 indicators)
    DQ-->>DS: Reject (flag "Poor Data")

    par Parallel Ingestion
        DQ->>NA: Validated news & events
        DQ->>SA: Validated financial data
    end

    NA->>NA: PhoBERT sentiment scoring (-1 to +1)
    SA->>SA: CANSLIM scoring + technical analysis

    NA->>DA: Sentiment context
    SA->>DA: Buy/Sell signal proposal

    DA->>DA: Spawn Bull & Bear personas
    Note over DA: Adversarial debate<br/>Bull argues growth<br/>Bear hunts risks

    DA->>PA: Synthesized risk report
    PA->>PA: Kelly Criterion + VaR calculation
    PA->>PA: Position sizing (Half-Kelly)

    par Alert Delivery
        PA->>TG: Tiered alert (L1/L2/L3)
        PA->>DB: Full analysis report
    end
```

## 2. Data Ingestion Pipeline

```mermaid
flowchart LR
    subgraph Sources
        VS[vnstock API]
        RSS[RSS Feeds]
        F319[Forum Scrapers]
    end

    subgraph Processing
        ETL[ETL Pipeline]
        NLP[PhoBERT NLP]
        EMB[Embedding Generator]
    end

    subgraph Storage
        PG[(PostgreSQL)]
        PGV[(pgvector)]
        RD[(Redis Cache)]
        S3[(S3 Archive)]
    end

    VS --> ETL --> PG
    ETL --> RD
    RSS --> NLP --> PGV
    F319 --> NLP
    NLP --> EMB --> PGV

    PG -.->|Backup| S3
```

## 3. LLM Model Routing

```mermaid
flowchart TD
    REQ[Incoming Request] --> ROUTER{Model Router}

    ROUTER -->|"Simple: news classification,<br/>data extraction"| LITE[Gemini 2.5 Flash-Lite<br/>$0.10/1M input]
    ROUTER -->|"Medium: real-time agent tasks,<br/>orchestration"| FLASH[Gemini 2.5 Flash<br/>$0.30/1M input]
    ROUTER -->|"Complex: financial analysis,<br/>debate, reasoning"| PRO[Gemini 2.5 Pro<br/>$1.25/1M input]

    LITE --> CACHE{Context Cache?}
    FLASH --> CACHE
    PRO --> CACHE

    CACHE -->|Hit| CACHED[Return cached response<br/>90% cost savings]
    CACHE -->|Miss| API[API call + cache result]
```

## 4. Alert System Flow

```mermaid
flowchart TD
    EVENT[Market Event Detected] --> CLASSIFY{Alert Level?}

    CLASSIFY -->|"Risk violation /<br/>Margin call"| L1["🔴 Level 1: URGENT<br/>Immediate Telegram push"]
    CLASSIFY -->|"Buy/Sell signal /<br/>Bull-Bear consensus"| L2["🟡 Level 2: TACTICAL<br/>Telegram + Dashboard"]
    CLASSIFY -->|"EOD summary /<br/>Corp events"| L3["🔵 Level 3: INFO<br/>Daily digest"]

    L1 --> TG[Telegram Bot]
    L2 --> TG
    L2 --> DASH[Dashboard]
    L3 --> TG
    L3 --> DASH
```

## 5. Human-in-the-Loop Flow

```mermaid
stateDiagram-v2
    [*] --> DataCollection
    DataCollection --> Analysis
    Analysis --> DebateResult

    DebateResult --> AutoExecute: Confidence > 80%
    DebateResult --> HumanReview: Confidence ≤ 80%

    HumanReview --> Approved: User approves
    HumanReview --> Rejected: User rejects
    HumanReview --> Modified: User modifies

    Approved --> AutoExecute
    Rejected --> [*]
    Modified --> Analysis: Re-analyze with constraints

    AutoExecute --> PortfolioUpdate
    PortfolioUpdate --> AlertDelivery
    AlertDelivery --> [*]
```

## 6. News Collection & Summarization Flow

Detailed implementation of how the News Agent collects, deduplicates, scrapes,
and summarizes articles before delivering reports to the user.

### 6.1 End-to-End Pipeline

```mermaid
sequenceDiagram
    participant CRON as ⏰ APScheduler (or Telegram)
    participant CL as 📡 NewsCollector
    participant DB as 🗄️ PostgreSQL Queue
    participant LLM1 as 🤖 Gemini (Stage 1: Flash-Lite)
    participant LLM2 as 🧠 Gemini (Stage 2: Flash)
    participant TG as 📱 Telegram Bot

    Note over CRON: Triggered by schedule<br/>or user command /news

    CRON->>CL: collect(hours_ago=24, persist=True)
    activate CL
    CL->>CL: Fetch RSS, Deduplicate, Scrape HTML
    CL-->>DB: Upsert Raw Articles (content_hash)
    deactivate CL

    CRON->>DB: get_unreported_articles_by_domain(limit=50)
    activate DB
    DB-->>CRON: List[NewsArticle] (Grouped by Topic e.g. 'macro')
    deactivate DB

    Note over CRON: Loop until DB Queue is empty

    opt Unsummarized Articles Exist
        CRON->>LLM1: generate_article_summaries(Batch)
        activate LLM1
        LLM1-->>CRON: List[(article_id, ai_summary)]
        deactivate LLM1
        CRON->>DB: update_summaries() (Set is_summarized=True)
    end

    CRON->>LLM2: synthesize_reports(All summaries for Topic)
    activate LLM2
    LLM2-->>CRON: Strategic Analysis & Grouping
    deactivate LLM2

    CRON->>TG: Send Topic Header [KINH TẾ VĨ MÔ]
    loop For each sub-topic
        CRON->>TG: Send synthesized message
    end

    CRON->>DB: mark_as_reported(article_ids)
```

### 6.2 Token Optimization Strategy

```mermaid
flowchart TD
    RAW["Raw HTML Page<br/>~200K–500K chars<br/>❌ ~50K–100K tokens"] -->|trafilatura.extract| CLEAN["Clean Text Body<br/>~2K–10K chars<br/>✅ ~500–2500 tokens"]
    CLEAN -->|"len > 15000?"| TRUNC{"Truncation Gate"}
    TRUNC -->|Yes| CUT["Truncated Text<br/>15,000 chars max<br/>~3,500 tokens"]
    TRUNC -->|No| PASS["Full Text<br/>(as-is)"]
    CUT --> LLM["Gemini API"]
    PASS --> LLM

    style RAW fill:#f66,color:#fff
    style CLEAN fill:#6b6,color:#fff
    style CUT fill:#fa0,color:#fff
    style PASS fill:#6b6,color:#fff
```

### 6.3 Key Design Decisions

| Decision | Rationale |
| :--- | :--- |
| Dedup **before** scraping | Avoids wasting HTTP requests on known articles |
| Trafilatura over BeautifulSoup | Purpose-built for article extraction; handles boilerplate removal automatically |
| `MAX_ARTICLE_CHARS = 15,000` | Keeps each article under ~3,500 tokens; prevents context window overflow |
| Graceful degradation on scrape failure | Falls back to short RSS summary; never crashes the pipeline |
| Persist **after** enrichment | DB always stores the richest version of the article available |
| `content_hash` = `SHA256(title\|link)[:16]` | Efficient cross-batch deduplication without full-text comparison |

### 6.4 Component Map

| Component | File | Responsibility |
| :--- | :--- | :--- |
| `RSSCollector` | `src/data/sources/rss_collector.py` | Async RSS feed fetching with concurrency control |
| `SourceRegistry` | `src/data/sources/rss_registry.py` | YAML-based source CRUD and filtering |
| `ArticleProcessor` | `src/data/processing/article_processor.py` | HTML cleanup, hash generation, deduplication |
| `HTMLScraper` | `src/data/sources/html_scraper.py` | Trafilatura-based full-text extraction |
| `NewsCollector` | `src/agents/news/collector.py` | High-level orchestrator composing the above |
| `NewsScheduler` | `src/agents/news/scheduler.py` | APScheduler cron + Telegram notification |
| `GeminiService` | `src/services/llm.py` | Two-stage LLM pipeline (see 6.5) |
| `NewsRepository` | `src/data/persistence/news_repo.py` | PostgreSQL upsert operations |

### 6.5 Two-Stage LLM Summarization Pipeline

The summarization uses a tiered model strategy to minimize cost while maximizing analysis quality.

```mermaid
flowchart TD
    subgraph "Stage 1 — Flash-Lite ($0.10/1M input)"
        A["282 enriched articles"] --> B{"Split into batches<br/>(30 articles/batch)"}
        B --> C1["Batch 1 → Flash-Lite"]
        B --> C2["Batch 2 → Flash-Lite"]
        B --> C3["..."]
        B --> CN["Batch 19 → Flash-Lite"]

        C1 --> D["Concise 2-4 sentence summaries<br/>per article (skip junk)"]
        C2 --> D
        C3 --> D
        CN --> D
    end

    subgraph "Stage 2 — Flash ($0.15/1M input)"
        D --> E["~250 summaries<br/>(~25K tokens total)"]
        E --> F["Flash: Group by topic<br/>Facts / Analysis / Conclusion"]
        F --> G["5-8 topic reports"]
    end

    G --> H["📱 Telegram delivery"]

    style A fill:#f66,color:#fff
    style D fill:#6b6,color:#fff
    style G fill:#36f,color:#fff
```

#### Cost Comparison (282 articles)

| Strategy | Stage 1 (Input) | Stage 2 (Input) | **Total Cost** |
| :--- | ---: | ---: | ---: |
| **Two-stage (current)** | ~339K tokens × $0.10/1M = $0.034 | ~25K tokens × $0.15/1M = $0.004 | **~$0.038** |
| Single-stage Flash | — | ~339K tokens × $0.15/1M = $0.051 | ~$0.051 |
| Single-stage Pro | — | ~339K tokens × $1.25/1M = $0.424 | ~$0.424 |

> Two-stage saves **~25%** vs single Flash and **~91%** vs Pro, while still producing Flash-quality analysis in the final output.

#### Configuration

| Parameter | Value | Location |
| :--- | :--- | :--- |
| `BATCH_SIZE` | 30 articles/batch | `src/services/llm.py` |
| `content_preview` limit | 3,000 chars/article | `src/services/llm.py` |
| Stage 1 model | `GEMINI__MODEL_LITE` | `.env` |
| Stage 2 model | `GEMINI__MODEL_FLASH` | `.env` |
| Stage 1 prompt | `src/prompts/news_batch_summarize.txt` | Flash-Lite optimized |
| Stage 2 prompt | `src/prompts/news_synthesis.txt` | Lena persona, topic grouping |

## 7. Financial Data Synchronization Flow

Detailed implementation of how the Financial Agent collects, validates, and persists
stock market data using an intelligent incremental sync strategy.

### 7.1 Bootstrap vs Incremental Decision

```mermaid
flowchart TD
    START["FinancialWorker.run_daily_sync()"] --> CHECK{"companies table<br/>empty?"}
    CHECK -->|Yes| BOOT["bootstrap_all_market()<br/>10-year deep fetch since 2015"]
    CHECK -->|No| INC["sync_all_market()<br/>Incremental sync"]

    INC --> BENCH["_get_market_latest_date()<br/>Query VNINDEX for actual latest trading day"]
    BENCH --> BULK["Bulk DB Query:<br/>get_all_latest_eod_dates()<br/>get_all_companies_last_updated()"]

    BULK --> LOOP{"For each ticker"}
    LOOP -->|"No profile or stale > 7d"| FULL["FULL sync<br/>(Profile + Financials + EOD)"]
    LOOP -->|"EOD < market_date"| EOD["EOD-only sync<br/>(1 API call, exact gap fill)"]
    LOOP -->|"EOD >= market_date"| SKIP["SKIP<br/>(0 API calls)"]

    FULL --> API["vnstock API<br/>(sleep 2s between calls)"]
    EOD --> API
    API --> DB["PostgreSQL<br/>Upsert + Commit"]
```

### 7.2 Stub Mechanism for Dead/New Tickers

```mermaid
flowchart LR
    FETCH["get_company_profile(VVS)"] -->|API returns None| STUB["Insert stub:<br/>{ticker: VVS, last_updated: now()}"]
    STUB --> SKIP_7D["Skipped for 7 days<br/>(last_updated check)"]
    SKIP_7D --> RETRY["After 7 days:<br/>Retry profile fetch"]

    FETCH -->|API returns data| FULL["Full upsert:<br/>Profile + Shareholders + Officers"]
    FULL --> SYNC["Continue to Financials + EOD"]
```

### 7.3 Key Design Decisions

| Decision | Rationale |
| :--- | :--- |
| **Market benchmark date** (not `today`) | Prevents re-syncing 800 tickers when API hasn't published today's candle yet (weekends, holidays, after-hours) |
| **Single bulk DB query** | One `SELECT MAX(trade_date) GROUP BY ticker` instead of 800 individual queries |
| **`from_date` passed to `sync_eod`** | Eliminates redundant per-ticker DB lookup inside `sync_eod` |
| **Sleep only after real API calls** | Skipped tickers don't waste 2s of rate-limit delay |
| **Stub insertion for dead tickers** | Prevents infinite retry loops; stub expires after 7 days |
| **Recursive NaN sanitizer** | Strips `float('NaN')` and `"NaN"` strings from nested JSONB before Postgres insertion |
| **`_parse_float()` for comma-formatted numbers** | Converts `"7,245.07"` → `7245.07` for DB float columns |

### 7.4 Component Map

| Component | File | Responsibility |
| :--- | :--- | :--- |
| `VnstockClient` | `src/data/sources/vnstock_client.py` | vnstock API wrapper with tenacity retry |
| `FinancialCollector` | `src/agents/financial/collector.py` | Orchestrates sync (bootstrap / incremental / market intelligence) |
| `FinancialWorker` | `src/agents/financial/worker.py` | APScheduler daily trigger + bootstrap detection |
| `FinancialRepository` | `src/data/persistence/financial_repo.py` | PostgreSQL upsert operations with NaN sanitization |
| `clean_nan_recursive()` | `src/data/persistence/financial_repo.py` | Recursive JSONB sanitizer for shareholders, officers, reports |

### 7.5 Market Intelligence Categories

| Category | Source | Sync Frequency | DB Table |
| :--- | :--- | :--- | :--- |
| Company Profiles | vnstock (VCI) | Weekly (7-day staleness) | `companies` |
| Financial Reports | vnstock (VCI) | Weekly | `financial_reports` |
| EOD OHLCV | vnstock (VCI) | Daily (market benchmark) | `stock_eod` |
| Mutual Funds | FMarket API | Daily | `mutual_fund_nav` |
| Gold Prices | VCI/VCB | Daily | `commodity_prices` |
| FX Rates | VCI/VCB | Daily | `commodity_prices` |
| Global Commodities | MSN Finance | Daily (404 fallback) | `commodity_prices` |
| Index Stats (VNINDEX, VN30) | vnstock (VCI) | Daily | `market_index_stats` |

