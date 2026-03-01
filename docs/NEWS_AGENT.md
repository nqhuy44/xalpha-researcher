# Feature: News Agent (Sentiment Sensor)

## Overview

The News Agent is the first sensory layer of the system. It continuously monitors multi-domain Vietnamese news sources and quantifies market sentiment using NLP.

## Responsibilities

- Ingest news from RSS feeds, financial APIs, and forum scrapers.
- Classify sentiment per article using PhoBERT (-1 to +1 score).
- Detect **tone shifts** in corporate reports and policy announcements.
- **Deduplicate** news to prevent "echo bias".
- Generate vector embeddings for RAG retrieval.

## Data Sources

| Source | Type | Domain |
|---|---|---|
| Cafef, VnExpress, Vietstock | RSS/API | Finance, macro |
| F319 (VnDirect forum) | Web scraping | Retail sentiment |
| Telegram/Zalo groups | Social listening | Rumors, crowd mood |
| Government Gazette | RSS | Law, regulations |
| International news | API/RSS | Geopolitics, trade policy |

## Domains Covered

- Finance & stock market
- Wars & geopolitics
- Economics & monetary policy
- Law & regulations (Luật Đất đai, Luật Nhà ở, etc.)
- Technology & AI

## Technical Design

| Component | Technology |
|---|---|
| NLP Model | PhoBERT (fine-tuned for Vietnamese financial terminology) |
| Sentiment Score | Float: -1.0 (very negative) to +1.0 (very positive) |
| Embedding | Generated via Gemini or PhoBERT for pgvector storage |
| LLM Assignment | Gemini 2.5 Flash-Lite (high-volume, low-cost) |

## Output Schema

```json
{
  "article_id": "uuid",
  "source": "cafef",
  "title": "...",
  "sentiment_score": 0.72,
  "domain": "finance",
  "mentioned_symbols": ["HPG", "VNM"],
  "embedding": [0.012, -0.034, ...],
  "published_at": "2026-02-24T10:00:00Z"
}
```

## API Contract

```
POST /api/v1/news/ingest      # Trigger ingestion cycle
GET  /api/v1/news/sentiment    # Get sentiment for symbol(s)
GET  /api/v1/news/recent       # Get recent news with scores
```
