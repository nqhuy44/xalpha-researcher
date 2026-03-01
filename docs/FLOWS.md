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
