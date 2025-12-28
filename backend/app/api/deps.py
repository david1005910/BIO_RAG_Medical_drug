"""API dependencies for dependency injection"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.services.rag_engine import RAGEngine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_rag_engine(
    session: AsyncSession,
) -> RAGEngine:
    """Get RAG engine dependency"""
    return RAGEngine(session=session)
