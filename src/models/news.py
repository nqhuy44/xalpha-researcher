"""
News-related Pydantic models (DTOs).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NewsArticleDTO(BaseModel):
    """Clean, normalized article ready for storage and analysis."""
    article_id: str
    content_hash: str
    url: str
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    content: str
    source_name: str
    domain: str
    language: str = "vi"
    published_at: datetime
    ingested_at: datetime


class ProcessingResult(BaseModel):
    """Result of processing a batch of articles."""
    articles: list[NewsArticleDTO]
    total_input: int
    total_output: int
    duplicates_removed: int


class CollectionResult(BaseModel):
    """Result of a full news collection cycle."""
    articles: list[NewsArticleDTO]
    total_fetched: int
    total_after_dedup: int
    sources_succeeded: int
    sources_failed: int
    duration_seconds: float
    errors: list[str]
