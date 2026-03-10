# Feature: News Agent (Sentiment Sensor)

**Status: ✅ Implemented**

## Overview

The News Agent is the first sensory layer of the system. It continuously monitors multi-domain Vietnamese news sources and quantifies market sentiment using NLP.

## Responsibilities

- Ingest news from RSS feeds and financial APIs using an async collector.
- **Synthesize** multi-domain news summaries using a two-stage Gemini pipeline (Stage 1: Summary, Stage 2: Synthesis).
- **Deduplicate** news content via hash-based processing to prevent exposure to "echo bias".
- Provide a unified context string for the Analyst Agent and Telegram reports.

## Data Sources

| Source | Type | Domain |
|---|---|---|
| Cafef, VnExpress, Vietstock | RSS/API | Finance, macro |
| Government Gazette | RSS | Law, regulations |
| International news | API/RSS | Geopolitics, trade policy |

## Technical Design

| Component | Technology | Status |
|---|---|---|
| **Summarization** | Gemini 2.5 Flash-Lite | ✅ Implemented |
| **Synthesis** | Gemini 2.5 Flash | ✅ Implemented |
| **Sentiment analysis** | PhoBERT (fine-tuned) | 🔲 Roadmap |
| **Embeddings** | pgvector / Gemini | 🔲 Roadmap |

## Output Schema (Internal DTO)

```python
class NewsArticleDTO(BaseModel):
    article_id: str
    content_hash: str
    url: str
    title: str
    content: str
    source_name: str
    domain: str
    description: Optional[str]
    published_at: datetime
```

## Report Workflow

1. **Stage 1**: Gemini Flash-Lite generates individual article summaries in batches.
2. **Stage 2**: Gemini Flash synthesizes all summaries into a single cohesive report per domain.
3. **Delivery**: Reports are pushed to Telegram using the async bot service.
