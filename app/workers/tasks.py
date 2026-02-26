import asyncio
from celery import Celery
from app.core.config import settings
from app.services.scraper import scrape_company_website
from app.services.ai_engine import analyze_text, generate_email, analyze_category_and_rating
from app.services.sender import send_email
# Import map radar
from app.services.maps_radar import search_local_leads
# DB Imports
from app.db.session import AsyncSessionLocal
from app.db import crud

# Initialize Celery App
celery_app = Celery(
    "ad_master_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Optional: Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="process_lead_pipeline")
def process_lead_task(url: str, my_offer: str, lead_id: int = None, contact_email: str = None):
    """
    I orchestrate the entire lead processing pipeline here: scraping, analysis, and email generation.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(_process_lead_async(url, my_offer, lead_id, contact_email))

async def _process_lead_async(url: str, my_offer: str, lead_id: int = None, contact_email: str = None):
    print(f"[TASK STARTED] Processing {url}...")
    
    # Step 1: I start by scraping the website using Playwright
    scrape_result = await scrape_company_website(url)
    if scrape_result.get("status") == "error":
        return {"status": "failed", "reason": f"Scraper error: {scrape_result.get('error')}"}
    
    raw_text = scrape_result.get("raw_text", "")
    emails = scrape_result.get("detected_emails", [])
    
    if not raw_text:
         return {"status": "failed", "reason": "Empty text from scraper"}

    # Step 2: I update the database with scraped content (emails & raw text)
    if lead_id:
        async with AsyncSessionLocal() as db:
            # We don't have get_lead_by_id exposed in CRUD, let's rely on session fetch
            from app.db.models import Lead
            from sqlalchemy import select
            
            result = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalars().first()
            
            if lead:
                lead.raw_text = raw_text
                lead.status = "analyzed"
                if emails and not lead.contact_email:
                    lead.contact_email = emails[0]
                    print(f"Saved email for lead {lead_id}: {lead.contact_email}")
                await db.commit()
    
    # Step 3: Then I analyze the content using AI
    analysis = await analyze_text(raw_text)
    if not analysis:
        return {"status": "failed", "reason": "AI Analysis failed to return structure"}

    # Step 4: Based on the analysis, I generate a personalized email draft
    email_body = await generate_email(analysis, my_offer)
    subject = f"Partnership with {analysis.summary[:20]}..."

    # Step 5: Finally, I save everything to the database as a draft
    if lead_id:
        async with AsyncSessionLocal() as db:
             await crud.save_draft(
                db, 
                lead_id=lead_id, 
                analysis=analysis.model_dump(), 
                subject=subject, 
                body=email_body
            )
             print(f"Draft saved for lead {lead_id}")

    print(f"[TASK FINISHED] for {url}")
    
    return {
        "status": "success",
        "company_name": analysis.summary,
        "relevance": analysis.relevance_score,
        "generated_email": email_body,
        "email_found": emails[0] if emails else None
    }

@celery_app.task(name="discover_leads_map")
def discover_leads_task(query: str, location: str, my_offer: str):
    """
    Radar Task:
    1. Search Google Maps (Serper)
    2. Iterate results
    3. If website -> Scrape (Recycle logic)
    4. If NO website + Low Rating -> Infer with AI
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_discover_leads_async(query, location, my_offer))

async def _discover_leads_async(query: str, location: str, my_offer: str):
    print(f"[RADAR STARTED] Searching '{query}' in '{location}'...")
    
    leads = await search_local_leads(query, location)
    results_log = []

    for lead in leads:
        name = lead.get("name")
        website = lead.get("website")
        rating = lead.get("rating", 5.0) or 5.0 # default to 5 if missing to be safe
        category = lead.get("category", "Unknown")
        
        print(f"Checking: {name} | Web: {website} | Rating: {rating}")
        
        try:
            analysis = None
            
            # STRATEGY A: Website exists -> Full Scrape
            if website:
                scrape_res = await scrape_company_website(website)
                if scrape_res.get("status") == "success" and scrape_res.get("raw_text"):
                    analysis = await analyze_text(scrape_res["raw_text"])
            
            # STRATEGY B: No Website but Low Rating -> Inference
            elif not website and rating < 4.2:
                print(f"Low rating detected without website. invoking AI Inference.")
                analysis = await analyze_category_and_rating(name, category, rating, location)

            # If we got an analysis from either strategy, prepare draft
            if analysis and analysis.relevance_score >= 6:
                email_body = await generate_email(analysis, my_offer)
                # In a real app, we would save to DB here using CRUD
                # For now, just log it
                results_log.append({
                    "name": name,
                    "strategy": "web" if website else "inference",
                    "email_draft": email_body[:50] + "..."
                })
        
        except Exception as e:
            print(f"Error processing lead {name}: {e}")
            continue

    print(f"[RADAR FINISHED] Processed {len(leads)} leads. Generated {len(results_log)} drafts.")
    return results_log
