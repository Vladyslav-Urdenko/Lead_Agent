import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Lead

async def check_emails():
    async with AsyncSessionLocal() as db:
        # Check leads with URLs
        result = await db.execute(
            select(Lead.id, Lead.name, Lead.url, Lead.contact_email)
            .where(Lead.url != None)
            .limit(20)
        )
        print("Leads WITH URLs:")
        for row in result.fetchall():
            name = row[1][:35] if row[1] else "N/A"
            email = row[3] if row[3] else "NO EMAIL"
            print(f"  ID: {row[0]}, Name: {name}, Email: {email}")
        
        # Count leads with emails
        result2 = await db.execute(
            select(Lead.id).where(Lead.contact_email != None)
        )
        count = len(result2.fetchall())
        print(f"\nTotal leads with emails: {count}")

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(check_emails())
