import asyncio
from app.db.session import engine
from app.db.models import Base

async def init_models():
    """
    Creates tables in the database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Uncomment for dev reset
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
