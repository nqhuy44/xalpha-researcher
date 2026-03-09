"""
Manual trigger for the 10-Year Financial Data Bootstrap.
This script performs a deep historical sync (EOD, Financials, Market Intelligence) 
starting from 2015-01-01 for all active tickers.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.agents.financial.collector import FinancialCollector
from src.db.session import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_bootstrap():
    """Run the 10-year bootstrap process."""
    logger.info("Initializing Database...")
    await init_db()
    
    collector = FinancialCollector()
    
    print("\n" + "="*60)
    print(f"{'10-YEAR FINANCIAL BOOTSTRAP':^60}")
    print("="*60)
    print("This will fetch:")
    print(" 1. All company profiles")
    print(" 2. 10 years of EOD data (from 2015-01-01)")
    print(" 3. 10 years of Financial Statements (Quarterly/Yearly)")
    print(" 4. Market Intelligence (Gold, FX, Commodities, Indices)")
    print("="*60)
    
    confirm = input("\nDo you want to proceed? (y/N): ")
    if confirm.lower() != 'y':
        print("Bootstrap cancelled.")
        return

    try:
        await collector.bootstrap_all_market()
        print("\n" + "="*60)
        print(f"{'BOOTSTRAP COMPLETED SUCCESSFULLY':^60}")
        print("="*60)
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_bootstrap())
    except KeyboardInterrupt:
        print("\nBootstrap interrupted by user.")
        sys.exit(0)
