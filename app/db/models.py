from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # URL can be null now if we find a business on Maps without a website
    url: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True) 
    name: Mapped[str] = mapped_column(String, nullable=True) # Added Name
    contact_email: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Added Contact Email
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="new")  # new, analyzed, drafted, sent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to EmailDrafts
    email_drafts: Mapped[List["EmailDraft"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(id={self.id}, url='{self.url}', status='{self.status}')>"

class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    
    # Storing the full JSON analysis from AI
    ai_analysis: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to Lead
    lead: Mapped["Lead"] = relationship(back_populates="email_drafts")

    def __repr__(self):
        return f"<EmailDraft(id={self.id}, lead_id={self.lead_id}, subject='{self.subject}')>"

class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

