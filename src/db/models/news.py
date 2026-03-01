"""
SQLAlchemy model for News articles.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class NewsArticle(Base):
    """
    SQLAlchemy model representing a news article.
    Matches the schema defined in documents/DATABASE.md.
    """
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(10), default="vi")
    
    # State & Summarization
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_summarized: Mapped[bool] = mapped_column(default=False, index=True)
    is_reported: Mapped[bool] = mapped_column(default=False, index=True)
    
    # Vector column will be added in Phase 2 for RAG
    # embedding: Mapped[Optional[Vector]] = mapped_column(Null, nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=None), index=True)

    def __repr__(self) -> str:
        return f"<NewsArticle(title='{self.title[:30]}...', source='{self.source_name}')>"


# Explicit indices for optimized querying
Index("idx_news_published_domain", NewsArticle.published_at.desc(), NewsArticle.domain)
Index("idx_news_unreported", NewsArticle.is_reported, NewsArticle.published_at.desc())
