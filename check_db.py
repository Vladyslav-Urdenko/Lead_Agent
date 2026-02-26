import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Lead

async def check_data():
    try:
        async with AsyncSessionLocal() as session:
            print("🔌 Connecting to database...")
            result = await session.execute(select(Lead))
            leads = result.scalars().all()
            print(f"✅ Connection Successful!")
            print(f"📊 Total Leads in DB: {len(leads)}")
            print("-" * 30)
            for lead in leads:
                print(f"🏢 Name: {lead.name}")
                print(f"   URL: {lead.url}")
                print(f"   Status: {lead.status}")
                print("-" * 30)
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
