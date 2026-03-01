"""
PostgreSQL session management using SQLAlchemy and asyncpg.
"""

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncSession,
)
from src.config.settings import settings

# Create async engine
engine = create_async_engine(
    settings.postgres.dsn,
    pool_size=settings.postgres.pool_size,
    echo=settings.app_debug,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    """Dependency for getting async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Ensure all database tables are created and up to date using Alembic."""
    from pathlib import Path
    from alembic.config import Config
    from alembic import command
    import asyncio
    
    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    
    def run_upgrade():
        """Run alembic upgrade head synchronously."""
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        command.upgrade(alembic_cfg, "head")

    # Run the synchronous alembic command in a thread pool
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_upgrade)
