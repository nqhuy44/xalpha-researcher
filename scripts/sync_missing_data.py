import asyncio
import logging
from datetime import datetime, timedelta
from src.agents.financial.collector import FinancialCollector
from src.data.persistence.financial_repo import FinancialRepository
from src.db.session import async_session_factory as SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    collector = FinancialCollector()
    
    async with SessionLocal() as session:
        repo = FinancialRepository(session)
        # 1. Fetch metadata for all tickers
        latest_eods = await repo.get_all_latest_eod_dates()
        companies_updated = await repo.get_all_companies_last_updated()
        
    logger.info("Fetching premium ticker list (Bluechip/Midcap)...")
    premium_tickers = set(await collector.vnstock.get_all_tickers())
    
    tickers_to_update = []
    
    for ticker, eod_info in latest_eods.items():
        if ticker not in premium_tickers:
            continue
            
        comp_info = companies_updated.get(ticker, {})
        
        has_technicals = eod_info['has_technicals']
        has_valuations = comp_info.get('has_valuations', False)
        
        if not has_technicals or not has_valuations:
            tickers_to_update.append((ticker, not has_valuations, not has_technicals))
    
    if not tickers_to_update:
        logger.info("All tickers already have technical indicators and valuations populated. Nothing to do!")
        return

    logger.info(f"Found {len(tickers_to_update)} tickers requiring data backfill (Valuations/Technicals).")
    
    # Batch processing to respect rate limits
    batch_size = 10
    try:
        for i in range(0, len(tickers_to_update), batch_size):
            batch = tickers_to_update[i:i + batch_size]
            logger.info(f"Processing batch: {[t[0] for t in batch]}")
            
            tasks = []
            for ticker, missing_v, missing_t in batch:
                # We use sync_all_data to ensure everything is refreshed if either is missing
                tasks.append(collector.sync_all_data(ticker))
                
            await asyncio.gather(*tasks)
            
            # Respect API rate limits (vnstock community is 60 req/min)
            if i + batch_size < len(tickers_to_update):
                logger.info("Waiting 2s for next batch to respect limits...")
                await asyncio.sleep(2)
    except SystemExit as se:
        logger.error(f"Rate limit triggered SystemExit: {se}")
        logger.info("Sync halted. Try again in a few minutes or upgrade to a higher tier.")

    logger.info("Data backfill completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
