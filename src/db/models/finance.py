"""
SQLAlchemy models for financial data.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, Float, Index, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base


class Company(Base):
    """
    SQLAlchemy model representing a listed company.
    """
    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    sector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Financial Overview
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ev_ebitda: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Detailed Profile Data
    shareholders: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    officers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<Company(ticker='{self.ticker}', name='{self.short_name}')>"


class FinancialReport(Base):
    """
    SQLAlchemy model for financial statements (Balance Sheet, Income Statement, Cash Flow).
    Uses JSONB for flexible schema across different industries.
    """
    __tablename__ = "financial_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # BalanceSheet, IncomeStatement, CashFlow
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # quarter, year
    year: Mapped[int] = mapped_column(nullable=False)
    quarter: Mapped[int] = mapped_column(nullable=False, default=0)  # 0 for yearly, 1-4 for quarterly
    
    # The actual financial data stored as JSONB
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint('ticker', 'report_type', 'period', 'year', 'quarter', name='uix_ticker_period_year_type'),
    )

    def __repr__(self) -> str:
        q_str = f"Q{self.quarter}" if self.quarter else "FY"
        return f"<FinancialReport(ticker='{self.ticker}', type='{self.report_type}', period='{self.year} {q_str}')>"


class StockEOD(Base):
    """
    End-of-day OHLCV trading data.
    Deduplication on (ticker, trade_date).
    """
    __tablename__ = "stock_eod"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Technical Indicators
    rsi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('ticker', 'trade_date', name='uix_ticker_trade_date'),
    )

    def __repr__(self) -> str:
        return f"<StockEOD(ticker='{self.ticker}', date='{self.trade_date}', close={self.close})>"


class MarketIndexStats(Base):
    """
    Market-wide statistics for indices (e.g., VNINDEX, VN30).
    Includes valuation ratios like P/E, P/B.
    """
    __tablename__ = "market_index_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    index_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    pe: Mapped[Optional[float]] = mapped_column(Float)
    pb: Mapped[Optional[float]] = mapped_column(Float)
    dividend_yield: Mapped[Optional[float]] = mapped_column(Float)
    market_cap: Mapped[Optional[float]] = mapped_column(Float)
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('index_code', 'trade_date', name='uix_index_trade_date'),
    )

    def __repr__(self) -> str:
        return f"<MarketIndexStats(index='{self.index_code}', date='{self.trade_date}', PE={self.pe})>"


class MacroIndicator(Base):
    """
    Macroeconomic indicators such as GDP, CPI, Interest Rates.
    """
    __tablename__ = "macro_indicators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('name', 'report_date', name='uix_macro_indicator_date'),
    )

    def __repr__(self) -> str:
        return f"<MacroIndicator(name='{self.name}', date='{self.report_date}', value={self.value})>"


class MutualFundNav(Base):
    """
    Historical NAV (Net Asset Value) for mutual funds.
    Data primarily from FMarket.
    """
    __tablename__ = "mutual_fund_nav"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    nav_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="FMARKET")
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('fund_code', 'nav_date', name='uix_fund_nav_date'),
    )

    def __repr__(self) -> str:
        return f"<MutualFundNav(fund='{self.fund_code}', date='{self.nav_date}', NAV={self.nav})>"


class CommodityPrice(Base):
    """
    Prices for commodities, FX rates, and global indices.
    """
    __tablename__ = "commodity_prices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g., GOLD, USDVND, XAU
    price_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'price_date', name='uix_commodity_price_date'),
    )

    def __repr__(self) -> str:
        return f"<CommodityPrice(symbol='{self.symbol}', date='{self.price_date}', price={self.price})>"


class StockTradingStats(Base):
    """
    Detailed trading statistics including bid/ask volumes and order flow.
    """
    __tablename__ = "stock_trading_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    total_buy_vol: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_sell_vol: Mapped[Optional[int]] = mapped_column(BigInteger)
    buy_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    sell_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint('ticker', 'trade_date', name='uix_ticker_trading_stats_date'),
    )

    def __repr__(self) -> str:
        return f"<StockTradingStats(ticker='{self.ticker}', date='{self.trade_date}', buy={self.total_buy_vol}, sell={self.total_sell_vol})>"

