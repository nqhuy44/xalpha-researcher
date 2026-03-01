import asyncio
import structlog
from src.config.settings import settings

logger = structlog.get_logger(__name__)

async def main():
    logger.info("xalpha_researcher_starting", version="0.1.2")
    logger.info("run_scripts", 
                bot="python -m src.interfaces.telegram.bot",
                scheduler="python scripts/run_scheduler.py")
    
if __name__ == "__main__":
    asyncio.run(main())
