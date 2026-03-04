import pytest
import asyncio
from src.agents.financial.collector import FinancialCollector
from src.db.session import async_session_factory as SessionLocal
from src.db.models.finance import Company, FinancialReport
from sqlalchemy import select

@pytest.mark.asyncio
async def test_financial_collection_and_deduplication():
    """
    Verifies that collecting data twice for the same ticker doesn't create duplicates.
    """
    ticker = "TCB"
    collector = FinancialCollector()
    
    # First sync
    await collector.sync_full_ticker(ticker)
    
    async with SessionLocal() as session:
        # Check company profile exists
        result = await session.execute(select(Company).where(Company.ticker == ticker))
        company = result.scalar_one_or_none()
        assert company is not None, f"Company {ticker} should have been created"
        
        # Count quarterly financial reports
        result = await session.execute(
            select(FinancialReport).where(FinancialReport.ticker == ticker, FinancialReport.period == "quarter")
        )
        q_count_1 = len(result.scalars().all())
        assert q_count_1 > 0, f"Quarterly reports should have been created for {ticker}"

        # Count yearly financial reports
        result = await session.execute(
            select(FinancialReport).where(FinancialReport.ticker == ticker, FinancialReport.period == "year")
        )
        y_count_1 = len(result.scalars().all())
        assert y_count_1 > 0, f"Yearly reports should have been created for {ticker}"
        
    # Second sync (should not increase count due to deduplication / upserts)
    await collector.sync_full_ticker(ticker)
    
    async with SessionLocal() as session:
        # Check quarterly count
        result = await session.execute(
            select(FinancialReport).where(FinancialReport.ticker == ticker, FinancialReport.period == "quarter")
        )
        q_count_2 = len(result.scalars().all())
        assert q_count_1 == q_count_2, f"Quarterly count changed from {q_count_1} to {q_count_2}"

        # Check yearly count
        result = await session.execute(
            select(FinancialReport).where(FinancialReport.ticker == ticker, FinancialReport.period == "year")
        )
        y_count_2 = len(result.scalars().all())
        assert y_count_1 == y_count_2, f"Yearly count changed from {y_count_1} to {y_count_2}"


