from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from typing import AsyncGenerator

# Create Async Engine
# echo=True prints SQL queries to console (useful for debugging)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, 
    future=True
)

# Call 'async_sessionmaker' to get a session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get DB session
    """
    async with AsyncSessionLocal() as session:
        yield session
