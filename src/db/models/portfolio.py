"""
SQLAlchemy models for Portfolio data.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, Integer, Text, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base


class PortfolioPosition(Base):
    """
    SQLAlchemy model representing a manually tracked portfolio holding.
    """
    __tablename__ = "portfolio_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cost_basis: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PortfolioPosition(symbol='{self.symbol}', shares={self.shares}, cost_basis={self.cost_basis})>"

class PortfolioSuggestion(Base):
    """
    SQLAlchemy model representing an AI-generated suggestion for a specific ticker.
    """
    __tablename__ = "portfolio_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Context from Analyst Graph (Judge)
    analyst_decision: Mapped[str] = mapped_column(String(255), nullable=False)
    analyst_confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Context from Portfolio Graph
    suggested_action: Mapped[str] = mapped_column(String(20), nullable=False)
    suggested_shares: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    suggested_cost: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verdict_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PortfolioSuggestion(symbol='{self.symbol}', action='{self.suggested_action}', shares={self.suggested_shares})>"
