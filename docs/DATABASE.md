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
    COMPANY ||--o{ AGENT_ANALYSIS : analyzed_by

    NEWS_ARTICLE ||--o{ SENTIMENT_SCORE : has
    AGENT_ANALYSIS ||--o{ DEBATE_RECORD : contains

    PORTFOLIO ||--o{ POSITION : holds
    POSITION }o--|| COMPANY : references
    PORTFOLIO ||--o{ ALERT : generates

    COMPANY {
        uuid id PK
        varchar symbol UK
        varchar name
        varchar exchange
        varchar sector
        varchar industry
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    FINANCIAL_REPORT {
        uuid id PK
        uuid company_id FK
        varchar report_type
        date period_end
        jsonb balance_sheet
        jsonb income_statement
        jsonb cash_flow
        float eps
        float roe
        float roa
        float pe_ratio
        float pb_ratio
        int schema_version
        jsonb raw_data
        timestamp created_at
    }

    STOCK_PRICE {
        uuid id PK
        uuid company_id FK
        date trading_date
        float open
        float high
        float low
        float close
        bigint volume
        float change_pct
        jsonb technical_indicators
    }

    NEWS_ARTICLE {
        uuid id PK
        varchar content_hash UK
        varchar url
        varchar title
        varchar author
        text description
        text content
        varchar source_name
        varchar domain
        varchar language
        vector embedding
        timestamp published_at
        timestamp ingested_at
    }

    SENTIMENT_SCORE {
        uuid id PK
        uuid article_id FK
        uuid company_id FK
        float score
        varchar model_version
        jsonb shap_values
        timestamp created_at
    }

    AGENT_ANALYSIS {
        uuid id PK
        uuid company_id FK
        varchar agent_type
        varchar signal
        float confidence
        jsonb canslim_scores
        jsonb technical_scores
        jsonb shap_breakdown
        jsonb raw_llm_response
        varchar model_used
        timestamp created_at
    }

    DEBATE_RECORD {
        uuid id PK
        uuid analysis_id FK
        text bull_argument
        text bear_argument
        text synthesis
        float risk_score
        varchar model_used
        int input_tokens
        int output_tokens
        timestamp created_at
    }

    PORTFOLIO {
        uuid id PK
        varchar name
        float total_value
        float cash_balance
        jsonb risk_params
        timestamp updated_at
    }

    POSITION {
        uuid id PK
        uuid portfolio_id FK
        uuid company_id FK
        int quantity
        float avg_cost
        float current_value
        float kelly_fraction
        float var_limit
        timestamp opened_at
        timestamp updated_at
    }

    ALERT {
        uuid id PK
        uuid portfolio_id FK
        int level
        varchar alert_type
        text message
        jsonb metadata
        boolean delivered
        timestamp created_at
    }

    INSIDER_TRADE {
        uuid id PK
        uuid company_id FK
        varchar insider_name
        varchar insider_role
        varchar transaction_type
        bigint shares
        float price
        date transaction_date
    }
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
| `agent_analysis` | `(company_id, created_at)` | Composite B-tree | Analysis history |
| `alert` | `(portfolio_id, delivered)` | Composite B-tree | Undelivered alert queue |

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
