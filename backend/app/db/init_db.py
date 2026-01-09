"""Database initialization script"""
import asyncio

from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine
from app.models import drug, search_log  # noqa: F401 - Import models for table creation


async def init_db():
    """Initialize database with required extensions and tables"""
    async with engine.begin() as conn:
        # Enable required PostgreSQL extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    print("Database initialized successfully!")


async def drop_db():
    """Drop all tables (use with caution)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("All tables dropped!")


if __name__ == "__main__":
    asyncio.run(init_db())
