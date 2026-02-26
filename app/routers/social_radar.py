from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db, AsyncSessionLocal
from app.db.models import Lead
from app.services.omni_radar import scan_social_media
from app.services import ai_engine, telegram_bot
from typing import List
import asyncio

router = APIRouter()

@router.post("/social", status_code=202)
async def trigger_social_radar(keywords: List[str], background_tasks: BackgroundTasks):
    """
    Triggers the Full Social Radar Pipeline:
    1. Scan Google/Social Media for keywords.
    2. Check duplicates in DB.
    3. AI Filter (News vs Human).
    4. Alert Telegram + Save to DB.
    """
    if not keywords:
        raise HTTPException(status_code=400, detail="Keywords list cannot be empty")
        
    background_tasks.add_task(run_social_radar_task, keywords)
    
    return {
        "status": "radar_started", 
        "keywords": keywords, 
        "message": "Social Radar is scanning the web. Leads will appear in Telegram and Database."
    }

async def run_social_radar_task(keywords: List[str]):
    print(f"📡 [RADAR] Starting scan for: {keywords}")
    
    # 1. Havest URLs
    findings = await scan_social_media(keywords)
    if not findings:
        print("   [RADAR] No results found.")
        return

    print(f"   [RADAR] Analyzing {len(findings)} raw findings...")

    # We need a DB session. Since this is a background task, we create a new session.
    async with AsyncSessionLocal() as db:
        for item in findings:
            url = item.get("link")
            snippet = item.get("snippet", "")
            source = item.get("source", "Unknown")
            title = item.get("title", "")

            # 2. Check Duplicates
            # Check if URL exists in Lead table
            result = await db.execute(select(Lead).where(Lead.url == url))
            existing_lead = result.scalars().first()
            
            if existing_lead:
                print(f"   [SKIP] Duplicate URL: {url}")
                continue

            # 3. AI Analysis (Is this a real person?)
            # Limit snippet length for AI to save tokens
            analysis = await ai_engine.analyze_social_lead(snippet[:1000], source)
            
            if analysis and analysis.is_lead:
                print(f"   🎯 [LEAD FOUND] {url} (Reason: {analysis.reason})")
                
                # 4. Save to DB
                new_lead = Lead(
                    url=url,
                    name=f"[{source}] {title[:100]}",
                    raw_text=snippet,
                    status="social_lead",  # New status for social leads
                    # No email yet
                )
                db.add(new_lead)
                await db.commit()
                
                # 5. Send Telegram Alert
                msg = (
                    f"📡 **SOCIAL RADAR ({source})**\n"
                    f"🗣️ **Snippet:** {snippet[:200]}...\n"
                    f"🔗 [Open Link]({url})\n"
                    f"💡 **AI Suggestion:** {analysis.suggested_reply}"
                )
                await telegram_bot.send_telegram_alert(msg)
                
            else:
                reason = analysis.reason if analysis else "AI failed or blocked"
                print(f"   [NOISE] {url} ({reason})")

    print("✅ [RADAR] Cycle Complete.")

