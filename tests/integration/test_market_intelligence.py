
import asyncio
import logging
from datetime import datetime
from src.agents.financial.collector import FinancialCollector
from src.db.session import async_session_factory as SessionLocal
from sqlalchemy import select
from src.db.models.finance import MutualFundNav, CommodityPrice, MarketIndexStats, StockTradingStats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_intelligence_sync():
    collector = FinancialCollector()
    
    logger.info("Testing Mutual Funds Sync...")
    fund_count = await collector.sync_funds()
    
    logger.info("Testing Commodities Sync...")
    comm_count = await collector.sync_commodities()

    logger.info("Testing Market Intelligence (Indices) Sync...")
    await collector.sync_market_intelligence()
    
    logger.info("Testing Stock Trading Stats Sync (FPT)...")
    stats_count = await collector.sync_stock_stats("FPT")
    
    # Verify in DB
    async with SessionLocal() as session:
        # Check indices
        idx_stmt = select(MarketIndexStats).limit(5)
        idx_res = await session.execute(idx_stmt)
        indices = idx_res.scalars().all()
        logger.info(f"Verified Indices in DB: {[(i.index_code, i.trade_date) for i in indices]}")

        # Check trading stats
        ts_stmt = select(StockTradingStats).where(StockTradingStats.ticker == "FPT").limit(1)
        ts_res = await session.execute(ts_stmt)
        stats = ts_res.scalar_one_or_none()
        if stats:
            logger.info(f"Verified Trading Stats for FPT: Buy={stats.total_buy_vol}, Sell={stats.total_sell_vol}")
        
    if fund_count > 0 or comm_count > 0:
        logger.info("PHASE 4 VERIFICATION SUCCESSFUL")
    else:
        logger.warning("PHASE 4 VERIFICATION: No records upserted. Check logs.")

if __name__ == "__main__":
    asyncio.run(test_market_intelligence_sync())
