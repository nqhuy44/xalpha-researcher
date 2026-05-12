"""
SQLAlchemy models for LLM observability: per-call usage and per-debate trace.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base


class DebateTrace(Base):
    """
    One row per debate run. Aggregated after the graph completes.
    Drives the "Cost per ticker" dashboard tile (O2).
    """
    __tablename__ = "debate_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Per-node breakdown: {node_name: {input_tokens, output_tokens, calls, latency_ms}}
    node_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # running | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)

    verdict_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("debate_verdicts.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<DebateTrace ticker='{self.ticker}' status='{self.status}' input={self.total_input_tokens}>"


class LLMUsage(Base):
    """
    One row per LLM call. Used to compute DebateTrace aggregates and spot hot spots (I2/O1).
    """
    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    debate_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("debate_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    node: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    role: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # success | error
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)

    def __repr__(self) -> str:
        return (
            f"<LLMUsage node='{self.node}' model='{self.model}' "
            f"in={self.input_tokens} out={self.output_tokens}>"
        )
