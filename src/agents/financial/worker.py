"""
Daily automation worker for financial data synchronization.
Uses APScheduler to trigger daily market-wide updates.
"""

import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.financial.collector import FinancialCollector
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialWorker:
    """
    Worker that schedules and runs financial data synchronization tasks.
    """
    
    def __init__(self):
        self.collector = FinancialCollector()
        self.scheduler = AsyncIOScheduler()

    async def run_daily_sync(self):
        """
        Task to run the daily market-wide synchronization.
        Checks if bootstrap is needed (database empty) before running incremental sync.
        """
        logger.info("Triggering financial data synchronization...")
        try:
            # 1. Determine if bootstrap is needed
            from src.db.session import async_session_factory as SessionLocal
            from src.db.models.finance import Company
            from sqlalchemy import select, func
            
            async with SessionLocal() as session:
                count_stmt = select(func.count()).select_from(Company)
                res = await session.execute(count_stmt)
                count = res.scalar()
            
            if count == 0:
                logger.info("Database is empty. Starting 10-YEAR BOOTSTRAP...")
                await self.collector.bootstrap_all_market()
            else:
                # 2. Incremental Sync
                logger.info(f"Found {count} companies. Running incremental market-wide sync...")
                # Sync Market-wide Stock Data (EOD, Profiles, Reports)
                await self.collector.sync_all_market(batch_size=10)
                
                # 3. Sync Market Intelligence (Macro, Funds, Commodities)
                await self.collector.sync_market_intelligence()
            
            logger.info("Financial data synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Error during financial sync: {e}", exc_info=True)

    def start(self):
        """
        Configures the scheduler and starts it without blocking.
        """
        sync_hour = settings.news.schedule_hours[1] if len(settings.news.schedule_hours) > 1 else 19
        logger.info(f"Starting Financial Worker. Daily sync scheduled at {sync_hour}:00.")
        
        self.scheduler.add_job(
            self.run_daily_sync,
            CronTrigger(hour=sync_hour, minute=0),
            name="daily_market_sync",
            replace_existing=True
        )
        self.scheduler.start()

    async def run_forever(self):
        """Keep the process alive."""
        self.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            logger.info("Financial Worker stopped.")

if __name__ == "__main__":
    worker = FinancialWorker()
    asyncio.run(worker.run_forever())
