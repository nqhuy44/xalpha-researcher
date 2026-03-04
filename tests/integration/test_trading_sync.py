import pytest
import asyncio
from sqlalchemy import select
from src.agents.financial.collector import FinancialCollector
from src.db.models.finance import Company, StockEOD
from src.db.session import async_session_factory as SessionLocal

@pytest.mark.asyncio
async def test_eod_and_rich_profile_sync():
    """
    Verifies that company mapping includes shareholders/officers 
    and EOD data is correctly synced and deduplicated.
    """
    ticker = "FPT"
    collector = FinancialCollector()
    
    # Run sync
    await collector.sync_company(ticker)
    await collector.sync_eod(ticker)
    
    async with SessionLocal() as session:
        # Check company profile
        result = await session.execute(select(Company).where(Company.ticker == ticker))
        company = result.scalar_one_or_none()
        assert company is not None
        assert company.shareholders is not None
        assert len(company.shareholders) > 0
        assert company.officers is not None
        assert len(company.officers) > 0
        
        # Check EOD data
        result = await session.execute(select(StockEOD).where(StockEOD.ticker == ticker))
        eod_count_1 = len(result.scalars().all())
        assert eod_count_1 > 0
        
    # Re-sync EOD (incremental sync should not add new records if same day)
    await collector.sync_eod(ticker)
    
    async with SessionLocal() as session:
        result = await session.execute(select(StockEOD).where(StockEOD.ticker == ticker))
        eod_count_2 = len(result.scalars().all())
        assert eod_count_1 == eod_count_2, f"EOD count changed after incremental sync: {eod_count_1} -> {eod_count_2}"
