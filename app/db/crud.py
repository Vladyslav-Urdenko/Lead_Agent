from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func
from app.db.models import Lead, EmailDraft, AppSetting
from app.services.ai_engine import DEFAULT_PROMPTS

# ... existing code ...

async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    """
    I use this helper to fetch a system setting. If it's missing, I return the default value so the app doesn't break.
    """
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalars().first()
    if setting:
         return setting.value
    return default

async def set_setting(db: AsyncSession, key: str, value: str, description: str = None):
    """
    I use this to create or update a configuration setting in the database.
    """
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalars().first()
    
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = AppSetting(key=key, value=value, description=description)
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    return setting

async def get_all_settings(db: AsyncSession):
    """
    I fetch all available settings at once here, returning them as a dictionary for easy access.
    """
    result = await db.execute(select(AppSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}

async def initialize_default_settings(db: AsyncSession):
    """
    I run this on startup to populate the database with default prompts if they don't exist yet.
    """
    current_settings = await get_all_settings(db)
    
    for key, val in DEFAULT_PROMPTS.items():
        if key not in current_settings:
            db.add(AppSetting(key=key, value=val["value"], description=val["description"]))
    
    if DEFAULT_PROMPTS: # Only commit if we have defaults to add
        await db.commit()

import datetime

async def create_lead(db: AsyncSession, url: str = None, name: str = None, raw_text: str = None) -> Lead:
    """
    Creates a new Lead in the database.
    """
    # Check if exists first (by URL if present)
    if url:
        existing_lead = await get_lead_by_url(db, url)
        if existing_lead:
            # Update raw_text if provided and return existing
            if raw_text:
                existing_lead.raw_text = raw_text
                await db.commit()
                await db.refresh(existing_lead)
            return existing_lead

    new_lead = Lead(url=url, name=name, raw_text=raw_text, status="new")
    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)
    return new_lead

async def get_lead_by_url(db: AsyncSession, url: str) -> Optional[Lead]:
    """
    Fetch a lead by its unique URL.
    """
    result = await db.execute(select(Lead).where(Lead.url == url))
    return result.scalars().first()

async def get_lead_by_id(db: AsyncSession, lead_id: int) -> Optional[Lead]:
    """
    Fetch a lead by its ID.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalars().first()

async def get_lead_by_name(db: AsyncSession, name: str) -> Optional[Lead]:
    """
    Fetch a lead by its Name.
    """
    result = await db.execute(select(Lead).where(Lead.name == name))
    return result.scalars().first()

async def get_all_leads(db: AsyncSession, skip: int = 0, limit: int = 100, status: Optional[str] = None):
    """
    Fetch all leads with pagination, newest first. Optionally filter by status.
    """
    stmt = select(Lead).order_by(desc(Lead.id))
    
    if status:
         if status == "not_sent":
             stmt = stmt.where(Lead.status != "sent")
         else:
             stmt = stmt.where(Lead.status == status)
    
    # Apply pagination last
    stmt = stmt.offset(skip).limit(limit)
             
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_leads_count(db: AsyncSession) -> int:
    """
    Count total leads.
    """
    # Use standard count
    result = await db.execute(select(func.count()).select_from(Lead))
    return result.scalar() or 0

async def get_today_leads_count(db: AsyncSession) -> int:
    """
    Count leads created today.
    """
    # For simplicity, filtering on python side to avoid DB dialect issues with dates for now, 
    # but normally func.date(Lead.created_at) works in PG.
    # However since Lead.created_at is timestamp with timezone, let's keep it simple.
    stmt = select(func.count()).select_from(Lead).where(func.date(Lead.created_at) == func.current_date())
    result = await db.execute(stmt)
    return result.scalar() or 0


async def save_draft(
    db: AsyncSession, 
    lead_id: int, 
    analysis: Optional[dict], 
    subject: str, 
    body: str
) -> EmailDraft:
    """
    Saves the generated email draft and links it to the lead.
    Also updates the Lead status to 'drafted'.
    """
    new_draft = EmailDraft(
        lead_id=lead_id,
        ai_analysis=analysis or {},
        subject=subject,
        body=body
    )
    db.add(new_draft)
    
    # Update lead status
    # We need to fetch the lead to update it properly in the session
    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalars().first()
    if lead:
        lead.status = "drafted"

    await db.commit()
    await db.refresh(new_draft)
    return new_draft

async def get_draft_by_lead_id(db: AsyncSession, lead_id: int) -> Optional[EmailDraft]:
    """
    Fetch the latest email draft for a specific lead.
    """
    result = await db.execute(
        select(EmailDraft)
        .where(EmailDraft.lead_id == lead_id)
        .order_by(EmailDraft.id.desc())
    )
    return result.scalars().first()

async def update_draft_text(
    db: AsyncSession, 
    lead_id: int, 
    new_subject: str, 
    new_body: str
) -> Optional[EmailDraft]:
    """
    Updates the text of the latest draft for a lead.
    """
    draft = await get_draft_by_lead_id(db, lead_id)
    if draft:
        draft.subject = new_subject
        draft.body = new_body
        await db.commit()
        await db.refresh(draft)
    return draft
