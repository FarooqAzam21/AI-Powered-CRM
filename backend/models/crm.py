from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contact(Base, TimestampMixin):
    __tablename__ = "crm_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    name = Column(String, default="")
    company = Column(String, default="")
    title = Column(String, default="")
    source = Column(String, default="email")
    last_interaction_at = Column(DateTime, nullable=True, index=True)
    sentiment = Column(String, default="neutral")
    relationship_score = Column(Float, default=0.0)

    lead = relationship("models.crm.Lead", back_populates="contact", uselist=False, cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_contact_user_email"),)


class Lead(Base, TimestampMixin):
    __tablename__ = "crm_leads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), index=True, nullable=False)
    score = Column(Float, default=0.0, index=True)
    label = Column(String, default="cold", index=True)
    confidence = Column(Float, default=0.0)
    recommended_next_action = Column(String, default="Review contact")
    buying_intent = Column(Float, default=0.0)
    urgency = Column(Float, default=0.0)
    hiring_intent = Column(Float, default=0.0)

    contact = relationship("models.crm.Contact", back_populates="lead")


class Interaction(Base, TimestampMixin):
    __tablename__ = "crm_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), index=True, nullable=False)
    gmail_message_id = Column(String, index=True, nullable=True)
    channel = Column(String, default="email")
    direction = Column(String, default="inbound")
    subject = Column(String, default="")
    snippet = Column(Text, default="")
    sentiment = Column(String, default="neutral")
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)

    contact = relationship("models.crm.Contact", back_populates="interactions")


class Activity(Base, TimestampMixin):
    __tablename__ = "crm_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), index=True, nullable=True)
    type = Column(String, index=True)
    title = Column(String)
    description = Column(Text, default="")
    status = Column(String, default="open", index=True)
    due_at = Column(DateTime, nullable=True, index=True)


class Note(Base, TimestampMixin):
    __tablename__ = "crm_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), index=True, nullable=True)
    body = Column(Text, nullable=False)


class Deal(Base, TimestampMixin):
    __tablename__ = "crm_deals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), index=True, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    stage = Column(String, default="prospecting", index=True)
    status = Column(String, default="open", index=True)
    value = Column(Float, default=0.0)
    probability = Column(Float, default=0.1)
    expected_close_at = Column(DateTime, nullable=True, index=True)
    actual_close_at = Column(DateTime, nullable=True)
    stage_moved_at = Column(DateTime, nullable=True)
    close_reason = Column(String, default="")
    ai_score = Column(Float, default=0.0)
    ai_recommendation = Column(Text, default="")

    contact = relationship("models.crm.Contact", foreign_keys=[contact_id])
    activities = relationship("DealActivity", back_populates="deal", cascade="all, delete-orphan")

    @property
    def name(self):
        return self.title

    @name.setter
    def name(self, value):
        self.title = value

    @property
    def expected_close_date(self):
        return self.expected_close_at

    @expected_close_date.setter
    def expected_close_date(self, value):
        self.expected_close_at = value

    @property
    def actual_close_date(self):
        return self.actual_close_at

    @actual_close_date.setter
    def actual_close_date(self, value):
        self.actual_close_at = value


class DealActivity(Base, TimestampMixin):
    __tablename__ = "crm_deal_activities"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("crm_deals.id"), index=True, nullable=False)
    activity_type = Column(String, default="note")
    description = Column(Text, default="")
    value_impact = Column(Float, default=0.0)
    probability_impact = Column(Float, default=0.0)

    deal = relationship("models.crm.Deal", back_populates="activities")


class CustomerProfile(Base, TimestampMixin):
    __tablename__ = "crm_customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    summary = Column(Text, default="")
    buyer_persona = Column(String, default="")
    buying_style = Column(String, default="")
    pain_points = Column(Text, default="[]")
    interests = Column(Text, default="[]")
    communication_style = Column(String, default="")
    engagement_level = Column(String, default="medium")
    company_industry = Column(String, default="")
    company_size = Column(String, default="")
    ai_model = Column(String, default="tinyllama")
    generated_at = Column(DateTime, nullable=True)

    contact = relationship("models.crm.Contact", foreign_keys=[contact_id])

    @property
    def last_updated_at(self):
        return self.updated_at


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    status = Column(String, default="draft")  # no index here to avoid duplicate with models/campaigns.py
    throttle_per_minute = Column(Integer, default=2)
    sent_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)


class CampaignRecipient(Base, TimestampMixin):
    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), nullable=True)
    email = Column(String, index=True, nullable=False)
    status = Column(String, default="queued", index=True)
    last_error = Column(Text, default="")
    sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)


class AIInsight(Base, TimestampMixin):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), nullable=True)
    insight_type = Column(String, index=True)
    payload = Column(Text, default="{}")
    confidence = Column(Float, default=0.0)


class EmailMetadata(Base, TimestampMixin):
    __tablename__ = "email_metadata"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    gmail_message_id = Column(String, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=True)
    sender = Column(String, index=True, default="")
    sender_email = Column(String, index=True, default="")
    subject = Column(String, default="")
    snippet = Column(Text, default="")
    label_ids = Column(Text, default="")
    internal_date = Column(DateTime, index=True, nullable=True)
    body_fetched = Column(Boolean, default=False, index=True)
    body_cache_key = Column(String, nullable=True)
    ai_status = Column(String, default="queued", index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_email_meta_user_gmail"),
        Index("ix_email_meta_user_date", "user_id", "internal_date"),
        Index("ix_email_meta_user_sender", "user_id", "sender_email"),
        Index("ix_email_meta_user_status", "user_id", "ai_status"),
    )


class EmailClassificationRule(Base, TimestampMixin):
    __tablename__ = "email_classification_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    sender_domain = Column(String, index=True, default="")
    sender_email = Column(String, index=True, default="")
    keywords = Column(Text, default="[]")
    source = Column(String, default="manual")
    match_count = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_email_rule_user_domain", "user_id", "sender_domain"),
        Index("ix_email_rule_user_category", "user_id", "category"),
    )


class GmailSyncCursor(Base, TimestampMixin):
    __tablename__ = "gmail_sync_cursors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    after_timestamp = Column(Integer, default=0)
    next_page_token = Column(String, nullable=True)
    last_history_id = Column(String, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)


class TaskRecord(Base, TimestampMixin):
    __tablename__ = "task_records"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    queue = Column(String, index=True)
    task_type = Column(String, index=True)
    status = Column(String, default="queued", index=True)
    progress = Column(Float, default=0.0)
    result = Column(Text, default="")
    error = Column(Text, default="")
