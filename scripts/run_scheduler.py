import asyncio
from src.agents.news.scheduler import NewsScheduler
from src.config.settings import settings

async def main():
    scheduler = NewsScheduler()
    await scheduler.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
