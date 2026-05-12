# Database Design — xalpha-researcher

## Overview

Multi-tier database architecture optimized for different data access patterns:

| Tier | Technology | Purpose | Latency |
|---|---|---|---|
| **Cache** | Redis 8 | Real-time prices, sessions, hot vectors | <100ms |
| **Primary** | PostgreSQL 16 | Relational SSOT + pgvector embeddings | <10ms |
| **Archive** | S3-compatible | PDF reports, agent inference logs | Async |

## Entity Relationship Diagram

```mermaid
erDiagram
    COMPANY ||--o{ FINANCIAL_REPORT : has
    COMPANY ||--o{ STOCK_PRICE : has
    COMPANY ||--o{ INSIDER_TRADE : has
    COMPANY ||--o{ NEWS_ARTICLE : mentioned_in
    COMPANY ||--o{ DEBATE_VERDICT : has
    COMPANY ||--o{ AGENT_ANALYSIS : analyzed_by

    NEWS_ARTICLE ||--o{ SENTIMENT_SCORE : has
    DEBATE_VERDICT ||--o{ DEBATE_RECORD : generated_from
    DEBATE_VERDICT ||--o| DEBATE_TRACE : traced_by
    DEBATE_TRACE ||--o{ LLM_USAGE : contains

    PORTFOLIO_POSITIONS }o--|| COMPANY : references

    COMPANY {
        uuid id PK
        varchar ticker UK
        varchar company_name
        varchar short_name
        varchar industry
        varchar sector
        float market_cap
        jsonb shareholders
        jsonb officers
        timestamp last_updated
    }

    FINANCIAL_REPORT {
        uuid id PK
        varchar ticker FK
        varchar report_type
        varchar period
        int year
        int quarter
        jsonb data
        timestamp ingested_at
    }

    STOCK_EOD {
        uuid id PK
        varchar ticker FK
        date trade_date
        float open
        float high
        float low
        float close
        bigint volume
        timestamp ingested_at
    }

    NEWS_ARTICLE {
        uuid id PK
        varchar content_hash UK
        varchar url
        varchar title
        text content
        text ai_summary
        varchar source_name
        varchar domain
        boolean is_summarized
        boolean is_reported
        timestamp published_at
        timestamp ingested_at
    }

    MUTUAL_FUND_NAV {
        uuid id PK
        varchar fund_code
        float nav
        timestamp nav_date
        varchar source
        timestamp ingested_at
    }

    COMMODITY_PRICE {
        uuid id PK
        varchar symbol
        float price
        varchar currency
        timestamp price_date
        timestamp ingested_at
    }

    MARKET_INDEX_STATS {
        uuid id PK
        varchar index_code
        float market_cap
        float pe
        float pb
        timestamp stat_date
        timestamp ingested_at
    }

    STOCK_TRADING_STATS {
        uuid id PK
        varchar ticker FK
        date trade_date
        bigint total_buy_vol
        bigint total_sell_vol
        int buy_count
        int sell_count
        timestamp ingested_at
    }

    DEBATE_VERDICT {
        uuid id PK
        varchar ticker FK
        varchar decision
        int confidence_score
        int bull_score
        int bear_score
        jsonb short_term
        jsonb medium_term
        jsonb long_term
        text judge_synthesis
        boolean is_active
        timestamp created_at
    }

    PORTFOLIO_POSITIONS {
        uuid id PK
        varchar symbol FK
        int shares
        float avg_price
        varchar notes
        timestamp created_at
        timestamp updated_at
    }

    DEBATE_TRACE {
        uuid id PK
        varchar ticker
        timestamp started_at
        timestamp finished_at
        int total_input_tokens
        int total_output_tokens
        int total_cached_tokens
        float total_cost_usd
        int total_latency_ms
        int total_llm_calls
        jsonb node_breakdown
        varchar status
        uuid verdict_id FK
    }

    LLM_USAGE {
        uuid id PK
        timestamp ts
        uuid debate_run_id FK
        varchar ticker
        varchar node
        varchar role
        varchar provider
        varchar model
        int input_tokens
        int output_tokens
        int cached_tokens
        int latency_ms
        varchar status
    }

    COMPANY ||--o{ FINANCIAL_REPORT : has
    COMPANY ||--o{ STOCK_EOD : has
    COMPANY ||--o{ STOCK_TRADING_STATS : has
```

## Indexing Strategy

| Table | Index | Type | Rationale |
|---|---|---|---|
| `company` | `symbol` | UNIQUE B-tree | Fast lookup by ticker |
| `stock_price` | `(company_id, trading_date)` | Composite B-tree | Time-series queries |
| `news_article` | `content_hash` | UNIQUE B-tree | Fast deduplication |
| `news_article` | `embedding` | IVFFlat (pgvector) | RAG similarity search |
| `news_article` | `published_at` | B-tree | Chronological queries |
| `news_article` | `domain` | B-tree | Domain-specific filtering |
| `sentiment_score` | `(company_id, created_at)` | Composite B-tree | Sentiment timeline |
| `financial_report` | `(company_id, period_end)` | Composite B-tree | Historical financials |
| `debate_verdicts` | `(ticker, is_active)` | Composite B-tree | Active verdict lookup |
| `agent_analysis` | `(company_id, created_at)` | Composite B-tree | Analysis history |
| `alert` | `(portfolio_id, delivered)` | Composite B-tree | Undelivered alert queue |
| `debate_traces` | `ticker` | B-tree | Per-ticker cost history |
| `debate_traces` | `started_at` | B-tree | Chronological trace queries |
| `llm_usage` | `ts` | B-tree | Chronological call log |
| `llm_usage` | `ticker` | B-tree | Per-ticker usage queries |
| `llm_usage` | `debate_run_id` | B-tree | Aggregation by debate run |

## Redis Cache Patterns

| Key Pattern | TTL | Purpose |
|---|---|---|
| `price:{symbol}` | 5s | Latest stock price |
| `sentiment:{symbol}` | 1h | Aggregated sentiment score |
| `canslim:{symbol}` | 24h | CANSLIM scores |
| `session:{user_id}` | 24h | Dashboard user session |
| `rate_limit:{api}` | Varies | API rate limit counters |

## News Storage Optimization

### Performance & Storage (TOAST)
PostgreSQL handles long text using **TOAST** (The Oversized-Attribute Storage Technique). 
- Articles with content > 2KB are stored outside the main data page.
- Performance on metadata queries (filtering by date, source, domain) remains extremely fast because the database only reads the `content` when explicitly requested.
- Sequential scans on metadata are not impacted by the size of the `content` field.

### Image Handling
The system follows a **Text-Only** policy for news articles:
- `ArticleProcessor` utilizes `BeautifulSoup` to strip all HTML tags including `<img>`, `<iframe>`, and `<script>`.
- Only normalized, unescaped text is stored in `content`.
- No binary data or image URLs are stored in the primary database.
