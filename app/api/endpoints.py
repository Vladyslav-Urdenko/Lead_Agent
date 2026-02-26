from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
# ... existing imports ...
from app.db import crud
from app.db.models import Lead, EmailDraft
from app.services import scraper, ai_engine, sender

router = APIRouter()

# --- Pydantic Schemas for Inputs ---
from app.workers.tasks import process_lead_task
from app.services import scraper, ai_engine, sender, maps_radar, telegram_bot

# ... existing imports ...

# --- Pydantic Schemas for Inputs ---
class ProcessLeadRequest(BaseModel):
    url: str
    my_offer: str

class ProcessLeadResponse(BaseModel):
    lead_id: int
    draft_id: int
    company_name: str
    draft_subject: str
    draft_body: str
    relevance_score: int
    lead_url: Optional[str] = None
    lead_email: Optional[str] = None

class SendEmailRequest(BaseModel):
    contact_email: Optional[str] = None

class UpdateDraftRequest(BaseModel):
    new_subject: str
    new_body: str

class DiscoverLeadsRequest(BaseModel):
    query: str
    location: str
    my_offer: str
    
class RadarRequest(BaseModel):
    query: str
    location: str

class LeadResponse(BaseModel):
    id: int
    name: Optional[str] = None
    url: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total_leads: int
    new_today: int

# --- Settings Endpoints ---

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """
    Get all application settings (prompts, API keys, etc).
    """
    # Ensure defaults exist
    await crud.initialize_default_settings(db)
    return await crud.get_all_settings(db)

class UpdateSettingRequest(BaseModel):
    value: str

@router.put("/settings/{key}")
async def update_setting(key: str, request: UpdateSettingRequest, db: AsyncSession = Depends(get_db)):
    """
    Update a specific setting.
    """
    await crud.set_setting(db, key, request.value)
    return {"status": "updated", "key": key}


# --- Endpoints ---

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get lead statistics: total count and new today.
    """
    total = await crud.get_leads_count(db)
    today = await crud.get_today_leads_count(db)
    return {"total_leads": total, "new_today": today}


@router.get("/", response_model=List[LeadResponse])
async def get_leads(
    skip: int = 0, 
    limit: int = 100, 
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all leads from the database. Optional status filter (e.g., 'new', 'sent', 'not_sent').
    """
    leads = await crud.get_all_leads(db, skip=skip, limit=limit, status=status)
    return leads

@router.post("/radar/maps")
async def radar_maps(
    request: RadarRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Search Google Maps via Serper, add leads to DB, and notify Telegram.
    Background: Scrapes website and prepares draft if website exists.
    """
    # 1. Search Serper
    leads = await maps_radar.search_local_leads(request.query, request.location)
    
    results = []
    
    for lead_data in leads:
        name = lead_data.get("name")
        website = lead_data.get("website")
        rating = lead_data.get("rating", 0)
        
        # Step A: Check Duplicates
        existing = None
        if website:
            existing = await crud.get_lead_by_url(db, website)
        if not existing and name:
             existing = await crud.get_lead_by_name(db, name)
             
        if existing:
            results.append({
                "name": name, 
                "status": "duplicate",
                "url": website
            })
            continue

        # Create Lead in DB
        new_lead = await crud.create_lead(db, url=website, name=name)
        results.append({
            "name": name, 
            "status": "added", 
            "id": new_lead.id,
            "url": website
        })

        # Step C: Telegram Alert (If low rating or just found)
        # Using a simple condition: if rating found, send alert
        alert_msg = (
            f"📍 *LOCAL LEAD FOUND (via Serper)*\n"
            f"Business: {name}\n"
            f"Rating: {rating} ⭐\n"
            f"Website: {website or 'None'}\n"
            f"Action: Lead added to DB."
        )
        background_tasks.add_task(telegram_bot.send_telegram_alert, alert_msg)

        # Step B: Trigger Background Processing (if website exists)
        if website:
             # Calling Celery task for heavy lifting
             # We assume a default generic offer or placeholder for now, 
             # as this endpoint doesn't take 'my_offer'. 
             # Ideally pass it in request or use a default.
             default_offer = "We offer industrial IoT solutions to optimize your operations."
             process_lead_task.delay(website, default_offer, new_lead.id)

    return {"status": "success", "found": len(leads), "details": results}

@router.post("/process", response_model=ProcessLeadResponse)
async def process_lead(
    request: ProcessLeadRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Full Pipeline: Scrape -> Analyze -> Generate Draft -> Save DB
    """
    # 1. Create or Get Lead
    lead = await crud.create_lead(db, url=request.url)
    
    # 2. Scrape
    print(f"Start scraping {request.url}...")
    try:
        scrape_result = await scraper.scrape_company_website(request.url)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(tb) # Print to server logs
        raise HTTPException(status_code=500, detail=f"Scraper Internal Error: {repr(e)} | Trace: {tb}")
    
    if scrape_result.get("status") == "error":
        raise HTTPException(status_code=400, detail=f"Scraping failed: {scrape_result.get('error')}")
        
    raw_text = scrape_result.get("raw_text", "")
    emails = scrape_result.get("detected_emails", [])
    
    if not raw_text:
        raise HTTPException(status_code=400, detail="Scraped content is empty.")

    # Update Lead with raw text and email if found
    lead.raw_text = raw_text
    lead.status = "analyzed"
    if emails and not lead.contact_email:
        lead.contact_email = emails[0] # Take the first one found
        
    await db.commit()

    # 3. Analyze
    analysis = await ai_engine.analyze_text(raw_text)
    if not analysis:
        raise HTTPException(status_code=500, detail="AI Analysis failed.")

    # 4. Generate Email
    draft_body = await ai_engine.generate_email(analysis, request.my_offer)
    subject = f"Partnership with {analysis.summary[:20]}..." # Simple subject generation
    
    # 5. Save Draft
    draft = await crud.save_draft(
        db, 
        lead_id=lead.id, 
        analysis=analysis.model_dump(), 
        subject=subject, 
        body=draft_body
    )

    return ProcessLeadResponse(
        lead_id=lead.id,
        draft_id=draft.id,
        company_name=analysis.summary,
        draft_subject=draft.subject,
        draft_body=draft.body,
        relevance_score=analysis.relevance_score,
        lead_url=lead.url,
        lead_email=lead.contact_email
    )

@router.get("/{lead_id}/draft")
async def get_draft(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get the latest draft for review. If not found, attempt JIT generation.
    """
    draft = await crud.get_draft_by_lead_id(db, lead_id)
    
    if not draft:
        # Check if lead exists
        lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = lead_result.scalars().first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # JIT GENERATION LOGIC
        try:
            analysis = None
            
            # 1. If we have raw text (from previous scrape), analyze it
            if lead.raw_text and len(lead.raw_text) > 50:
                 prompt = await crud.get_setting(db, "analyze_text")
                 analysis = await ai_engine.analyze_text(lead.raw_text, custom_prompt=prompt)
            
            # 2. If no text but we have a URL, try to scrape now (fast mode)
            elif lead.url:
                 # In a real app, maybe too slow for GET, but let's try
                 scrape_res = await scraper.scrape_company_website(lead.url)
                 if scrape_res.get("raw_text"):
                     # Update lead with scraped text
                     lead.raw_text = scrape_res["raw_text"]
                     await db.commit()
                     
                     prompt = await crud.get_setting(db, "analyze_text")
                     analysis = await ai_engine.analyze_text(lead.raw_text, custom_prompt=prompt)
            
            # 3. If no URL and no text, try to infer from Name (Radar leads)
            elif lead.name and (not lead.raw_text or len(lead.raw_text) < 50):
                 # We assume it's a local business since it came from Radar
                 # We don't have category/rating stored, so we guess or use generic
                 print(f"Start JIT AI analysis for {lead.name}")
                 
                 prompt = await crud.get_setting(db, "infer_lead")
                 analysis = await ai_engine.analyze_category_and_rating(
                     business_name=lead.name,
                     category="Local Business", # Generic fallback
                     rating=4.0, # Neutral assumption
                     location="Berlin", # Context assumption or would need to store valid location
                     custom_prompt=prompt
                 )

            if analysis:
                # Generate EMAIL
                my_offer = await crud.get_setting(db, "my_offer", default="We help local businesses automate their workflows.")
                email_prompt = await crud.get_setting(db, "generate_email")
                
                email_body = await ai_engine.generate_email(analysis, my_offer, custom_prompt=email_prompt)
                
                # Save draft
                draft = await crud.save_draft(
                    db,
                    lead_id=lead_id,
                    analysis=analysis.model_dump(),
                    subject=f"Question regarding {lead.name}", # Simple subject
                    body=email_body
                )
                return draft

        except Exception as e:
            print(f"JIT Draft Generation Failed: {e}")
            # Fallthrough to empty template
        
        # Return empty template for manual drafting if generation failed
        return {
            "id": None,
            "lead_id": lead_id,
            "subject": "",
            "body": "",
            "ai_analysis": {}
        }
    return draft

@router.put("/{lead_id}/draft")
async def update_draft(
    lead_id: int, 
    request: UpdateDraftRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Edit and save the draft before approval. If draft doesn't exist, create one.
    """
    # Try to update existing first
    draft = await crud.update_draft_text(
        db, 
        lead_id, 
        request.new_subject, 
        request.new_body
    )
    
    # If no draft exists, create a new manual draft
    if not draft:
        # Verify lead exists first
        lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
        if not lead_result.scalars().first():
             raise HTTPException(status_code=404, detail="Lead not found")

        draft = await crud.save_draft(
            db,
            lead_id=lead_id,
            analysis={}, # Empty analysis for manual draft
            subject=request.new_subject,
            body=request.new_body
        )
    
    return {"status": "updated", "draft_id": draft.id, "subject": draft.subject}


@router.post("/{lead_id}/send")
async def send_draft(
    lead_id: int, 
    request: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approves and sends the latest draft for a lead.
    """
    # Get the latest draft for this lead
    result = await db.execute(
        select(EmailDraft)
        .where(EmailDraft.lead_id == lead_id)
        .order_by(EmailDraft.id.desc())
    )
    draft = result.scalars().first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="No drafts found for this lead.")

    # Determine recipient email
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalars().first()
    
    recipient = request.contact_email
    if not recipient and lead and lead.contact_email:
        recipient = lead.contact_email
    
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient email is required. Provide 'contact_email' or ensure lead has one.")

    # Send Email
    success = await sender.send_email(
        to_email=recipient,
        subject=draft.subject,
        body=draft.body
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email.")

    # Update DB status
    draft.is_approved = True
    
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalars().first()
    if lead:
        lead.status = "sent"
    
    await db.commit()

    return {"status": "success", "message": "Email queued/sent", "lead_id": lead_id}
