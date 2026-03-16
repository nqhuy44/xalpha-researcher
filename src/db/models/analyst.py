"""
SQLAlchemy models for Analyst/Debate data.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base


class DebateVerdict(Base):
    """
    Persistence model for the AI Judge's verdict on a specific ticker.
    Used for historical tracking and Portfolio Agent integration.
    """
    __tablename__ = "debate_verdicts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    decision: Mapped[str] = mapped_column(String(20), nullable=False) # BUY, HOLD, SELL
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    bull_score: Mapped[int] = mapped_column(nullable=False)
    bear_score: Mapped[int] = mapped_column(nullable=False)
    
    # Store complete JSON object of horizon predictions (outlook, entry, target, stop_loss, rationale)
    short_term: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    medium_term: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    long_term: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    context_layer_assessment: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    judge_synthesis: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Optional Referee Verification data
    referee_action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # CONFIRM, OVERRIDE, INCONCLUSIVE
    is_referee_valid: Mapped[Optional[bool]] = mapped_column(nullable=True)
    referee_synthesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Store complete list of debate rounds (arguments and rebuttals)
    debate_rounds: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Store complete history of referee interactions
    referee_history: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(default=True, index=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)

    def __repr__(self) -> str:
        active_str = "[ACTIVE]" if self.is_active else "[EXPIRED]"
        return f"<DebateVerdict {active_str} ticker='{self.ticker}', decision='{self.decision}', confidence={self.confidence_score}>"
