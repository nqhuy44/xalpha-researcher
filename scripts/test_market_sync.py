import asyncio
import logging
from src.agents.financial.collector import FinancialCollector

logging.basicConfig(level=logging.INFO)

async def test_market_discovery():
    collector = FinancialCollector()
    tickers = collector.vnstock.get_all_tickers()
    print(f"Discovered {len(tickers)} tickers.")
    if tickers:
        print(f"Sample tickers: {tickers[:10]}")
    
    # Test batch sync with just 2 tickers to verify logic
    if len(tickers) >= 2:
        test_batch = tickers[:2]
        print(f"Testing sync for batch: {test_batch}")
        # Manual call to sync_full_ticker for the batch
        tasks = [collector.sync_full_ticker(t) for t in test_batch]
        await asyncio.gather(*tasks)
        print("Batch sync test completed.")

if __name__ == "__main__":
    asyncio.run(test_market_discovery())
