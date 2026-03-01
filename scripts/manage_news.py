"""
CLI tool for managing News Agent sources and running manual collections.

Usage:
  python scripts/manage_news.py list
  python scripts/manage_news.py add "Source Name" "https://url.com/rss" finance --priority 2
  python scripts/manage_news.py disable "Source Name"
  python scripts/manage_news.py collect --domains finance --hours 24 --limit 10
  python scripts/manage_news.py telegram
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path if needed
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.agents.news.collector import NewsCollector
from src.agents.news.scheduler import NewsScheduler
from src.communication.telegram_bot import TelegramService
from src.data.sources.rss_registry import SourceRegistry
from src.config.settings import settings
from src.db.base import Base
from src.db.session import engine

def print_banner(text: str):
    print(f"\n{'='*60}\n{text:^60}\n{'='*60}")

async def handle_list(args):
    registry = SourceRegistry(settings.news.sources_path)
    registry.load()
    stats = registry.get_stats()
    
    print_banner(f"NEWS SOURCES (Total: {stats['total']})")
    print(f"{'NAME':<30} | {'DOMAIN':<12} | {'STATUS':<8} | {'PRIO'}")
    print("-" * 60)
    
    for s in registry.sources:
        status = "ENABLED" if s.enabled else "DISABLED"
        print(f"{s.name[:30]:<30} | {s.domain:<12} | {status:<8} | {s.priority}")
    print()

async def handle_add(args):
    registry = SourceRegistry(settings.news.sources_path)
    registry.load()
    try:
        registry.add_source(
            name=args.name,
            url=args.url,
            domain=args.domain,
            priority=args.priority
        )
        print(f"Successfully added source: {args.name}")
    except ValueError as e:
        print(f"Error: {e}")

async def handle_remove(args):
    registry = SourceRegistry(settings.news.sources_path)
    registry.load()
    if registry.remove_source(args.name):
        print(f"Successfully removed source: {args.name}")
    else:
        print(f"Source not found: {args.name}")

async def handle_toggle(args, enabled: bool):
    registry = SourceRegistry(settings.news.sources_path)
    registry.load()
    ok = registry.enable_source(args.name) if enabled else registry.disable_source(args.name)
    if ok:
        print(f"Successfully {'enabled' if enabled else 'disabled'} source: {args.name}")
    else:
        print(f"Source not found: {args.name}")

async def handle_collect(args):
    collector = NewsCollector()
    
    # Resolve time
    since = None
    if args.hours:
        since = datetime.now(tz=timezone.utc) - timedelta(hours=args.hours)
    elif args.weeks:
        since = datetime.now(tz=timezone.utc) - timedelta(weeks=args.weeks)
    elif args.months:
        since = datetime.now(tz=timezone.utc) - timedelta(days=args.months * 30)
    
    print(f"Collecting news...")
    print(f" - Domains: {args.domains or 'All'}")
    print(f" - Since: {since if since else 'Epoch'}")
    print(f" - Limit: {args.limit or settings.news.default_limit} per source")
    print(f" - Persist: {args.persist}")
    
    result = await collector.collect(
        domains=args.domains,
        since=since,
        limit=args.limit,
        persist=args.persist
    )
    
    print_banner("COLLECTION RESULT")
    print(f"Sources Succeeded: {result.sources_succeeded}")
    print(f"Sources Failed:    {result.sources_failed}")
    print(f"Articles Fetched:  {result.total_fetched}")
    print(f"After Deduplication: {result.total_after_dedup}")
    print(f"Duration:          {result.duration_seconds}s")
    
    if result.articles:
        print("\nLatest 5 articles:")
        for a in result.articles[:5]:
            print(f" [{a.domain:10}] {a.source_name}: {a.title}")

async def handle_schedule(args):
    scheduler = NewsScheduler()
    print_banner("NEWS SCHEDULER STARTED")
    print(f"Schedule: {settings.news.schedule_hours} (Vietnam Time)")
    print("Press Ctrl+C to stop.")
    await scheduler.run_forever()

async def handle_telegram(args):
    bot = TelegramService()
    print_banner("TELEGRAM BOT STARTED")
    print("Press Ctrl+C to stop.")
    bot.run_forever()

async def init_db_script():
    """Ensure tables exist before running."""
    from src.db.session import init_db
    await init_db()

def main():
    parser = argparse.ArgumentParser(description="XAlpha News Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # List
    subparsers.add_parser("list", help="List all news sources")

    # Add
    add_parser = subparsers.add_parser("add", help="Add a new RSS source")
    add_parser.add_argument("name", help="Source name")
    add_parser.add_argument("url", help="RSS feed URL")
    add_parser.add_argument("domain", help="Domain (finance, tech, law, etc.)")
    add_parser.add_argument("--priority", type=int, default=1, help="Priority (1-5)")

    # Remove
    rem_parser = subparsers.add_parser("remove", help="Remove a source")
    rem_parser.add_argument("name", help="Source name to remove")

    # Enable/Disable
    en_parser = subparsers.add_parser("enable", help="Enable a source")
    en_parser.add_argument("name", help="Source name to enable")
    dis_parser = subparsers.add_parser("disable", help="Disable a source")
    dis_parser.add_argument("name", help="Source name to disable")

    # Collect
    coll_parser = subparsers.add_parser("collect", help="Run manual news collection")
    coll_parser.add_argument("--domains", nargs="+", help="Filter by domains")
    coll_parser.add_argument("--hours", type=int, help="Limit to last X hours")
    coll_parser.add_argument("--weeks", type=int, help="Limit to last X weeks")
    coll_parser.add_argument("--months", type=int, help="Limit to last X months")
    coll_parser.add_argument("--limit", type=int, help="Limit articles per source")
    coll_parser.add_argument("--persist", action="store_true", help="Save to database")

    # Schedule
    subparsers.add_parser("schedule", help="Start the periodic news collector scheduler")

    # Telegram
    subparsers.add_parser("telegram", help="Start the Telegram Bot")

    # Migrate
    subparsers.add_parser("migrate", help="Run database migrations (Alembic)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Init DB tables first
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db_script())

    if args.command == "list":
        loop.run_until_complete(handle_list(args))
    elif args.command == "add":
        loop.run_until_complete(handle_add(args))
    elif args.command == "remove":
        loop.run_until_complete(handle_remove(args))
    elif args.command == "enable":
        loop.run_until_complete(handle_toggle(args, True))
    elif args.command == "disable":
        loop.run_until_complete(handle_toggle(args, False))
    elif args.command == "collect":
        loop.run_until_complete(handle_collect(args))
    elif args.command == "schedule":
        loop.run_until_complete(handle_schedule(args))
    elif args.command == "telegram":
        loop.run_until_complete(handle_telegram(args))
    elif args.command == "migrate":
        print("Migrations are automatically run on startup. Ensuring fully migrated...")
        loop.run_until_complete(init_db_script())
        print("Done.")

if __name__ == "__main__":
    main()
