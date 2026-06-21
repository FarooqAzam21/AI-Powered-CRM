from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

# =================== USER & AUTH ===================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    # Google OAuth
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    gmail_connected = Column(Boolean, default=False)
    
    # Relationships
    contacts = relationship("auth.models.Contact", back_populates="user", cascade="all, delete-orphan")
    leads = relationship("auth.models.Lead", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("auth.models.Activity", back_populates="user", cascade="all, delete-orphan")
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("models.campaigns.Campaign", back_populates="user", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =================== CONTACTS & LEADS ===================
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    name = Column(String)
    company = Column(String)
    title = Column(String)
    phone = Column(String)
    
    # Engagement
    interaction_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime)
    score = Column(Float, default=0.0)  # Lead quality score
    
    # Attributes
    is_active = Column(Boolean, default=True)
    is_prospect = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    meta_info = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="contacts")
    activities = relationship("auth.models.Activity", back_populates="contact", cascade="all, delete-orphan")
    leads = relationship("auth.models.Lead", back_populates="contact", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    
    # Lead Status
    status = Column(String, default="new")  # new, qualified, nurturing, converted, lost
    score = Column(Float, default=0.0)
    temperature = Column(String, default="cold")  # cold, warm, hot
    
    # Lead Details
    source = Column(String)  # email, import, web, referral
    industry = Column(String)
    company_size = Column(String)
    budget = Column(String)
    timeline = Column(String)
    
    # Engagement
    last_contacted_at = Column(DateTime)
    next_follow_up_at = Column(DateTime)
    follow_up_count = Column(Integer, default=0)
    
    # AI Insights
    intent_detected = Column(String)  # hiring, buying, general
    sentiment = Column(String)  # positive, neutral, negative
    ai_notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="leads")
    contact = relationship("auth.models.Contact", back_populates="leads")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =================== ACTIVITIES ===================
class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    
    type = Column(String)  # email_sent, email_received, call, meeting, note, task_completed
    subject = Column(String)
    description = Column(Text)
    
    # Details
    direction = Column(String)  # inbound, outbound
    status = Column(String, default="completed")
    
    # Relationships
    user = relationship("User", back_populates="activities")
    contact = relationship("auth.models.Contact", back_populates="activities")
    
    created_at = Column(DateTime, default=datetime.utcnow)

# =================== EMAILS ===================
class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    
    gmail_message_id = Column(String, unique=True, index=True)
    gmail_thread_id = Column(String, index=True)
    
    sender = Column(String, nullable=False)
    recipient = Column(String)
    subject = Column(String)
    body = Column(Text)
    
    # AI Analysis
    category = Column(String)
    confidence = Column(Float)
    action = Column(String)
    reason = Column(Text)
    draft_reply = Column(Text, nullable=True)
    sentiment = Column(String)
    
    # Status
    status = Column(String, default="PENDING")  # PENDING, SENT, ARCHIVED, ESCALATED
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="emails")
    
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.utcnow)


# =================== NOTIFICATIONS ===================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String)  # INFO, URGENT, SUCCESS, WARNING
    is_read = Column(Boolean, default=False)
    
    action_url = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    created_at = Column(DateTime, default=datetime.utcnow)

# =================== PHASE 6: ADVANCED CRM ===================

# Deal & Pipeline Models
class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    
    # Deal Info
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    value = Column(Float, default=0.0)  # Deal amount
    currency = Column(String, default="USD")
    
    # Pipeline Stage
    stage = Column(String, default="prospecting")  # prospecting, qualification, proposal, negotiation, won, lost
    stage_moved_at = Column(DateTime, default=datetime.utcnow)
    
    # Probability & Timeline
    probability = Column(Float, default=0.0)  # 0-100
    expected_close_date = Column(DateTime)
    actual_close_date = Column(DateTime)
    
    # Deal Status
    status = Column(String, default="open")  # open, won, lost
    close_reason = Column(String)  # If lost: why?
    
    # AI Insights
    ai_score = Column(Float, default=0.0)  # AI-predicted probability
    ai_recommendation = Column(Text)  # Next action recommendation
    
    # Relationships
    user = relationship("User", back_populates="deals")
    contact = relationship("auth.models.Contact", back_populates="deals")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Relationship Model - Email relationships between contacts
class ContactRelationship(Base):
    __tablename__ = "contact_relationships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    from_contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    to_contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    
    # Relationship Type
    relationship_type = Column(String)  # mentions, cc'd with, replied_to, forwarded_to
    email_count = Column(Integer, default=1)  # How many emails connect them
    last_interaction = Column(DateTime)
    
    # Strength
    strength = Column(Float, default=0.0)  # 0-100 based on interaction frequency
    
    # Inferred Relationship
    inferred_role = Column(String)  # manager, peer, subordinate, external partner, etc.
    
    # Relationships
    user = relationship("User", back_populates="relationships")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# AI Recommendation Model
class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True)
    
    # Recommendation
    recommendation_type = Column(String)  # next_action, best_time, template_use, follow_up_needed, etc.
    title = Column(String, nullable=False)
    description = Column(Text)
    action_items = Column(JSON, default=list)
    
    # Confidence
    confidence_score = Column(Float, default=0.0)  # 0-100
    reasoning = Column(Text)  # Why this recommendation?
    
    # Status
    status = Column(String, default="pending")  # pending, actioned, dismissed, expired
    actioned_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="recommendations")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Recommendation relevance expires

# Update User relationships to include Phase 6 models
User.deals = relationship("auth.models.Deal", back_populates="user", cascade="all, delete-orphan")
User.profiles = relationship("models.crm.CustomerProfile", cascade="all, delete-orphan")
User.relationships = relationship("ContactRelationship", back_populates="user", cascade="all, delete-orphan")
User.recommendations = relationship("AIRecommendation", back_populates="user", cascade="all, delete-orphan")

# Update Contact relationships to include Phase 6 models
Contact.deals = relationship("auth.models.Deal", back_populates="contact", cascade="all, delete-orphan")

# =================== PHASE 7: ADVANCED ANALYTICS ===================

class WinLossAnalysis(Base):
    __tablename__ = "win_loss_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    
    # Outcome
    outcome = Column(String)  # won, lost
    outcome_date = Column(DateTime)
    
    # Analysis
    root_cause = Column(String)  # Reason for win/loss
    key_factors = Column(JSON, default=list)  # AI-identified factors
    competitor = Column(String)  # If lost, who won?
    competitor_solution = Column(String)  # What they offered
    
    # Deal Context
    final_value = Column(Float)
    sales_cycle_days = Column(Integer)  # Days from prospecting to close
    contact_count = Column(Integer)  # Stakeholders involved
    interaction_count = Column(Integer)  # Total touchpoints
    
    # Lessons Learned
    lessons_learned = Column(JSON, default=list)  # Key insights
    recommendations = Column(Text)  # What to do differently
    
    # Relationships
    user = relationship("User", back_populates="win_loss_analyses")
    deal = relationship("auth.models.Deal", back_populates="win_loss")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SalesCycleMetrics(Base):
    __tablename__ = "sales_cycle_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Period
    period_start = Column(DateTime)  # Analytics period (month, quarter)
    period_end = Column(DateTime)
    period_type = Column(String)  # monthly, quarterly, yearly
    
    # Cycle Metrics
    avg_sales_cycle_days = Column(Float)  # Average days to close
    median_sales_cycle_days = Column(Float)
    fastest_close_days = Column(Integer)
    slowest_close_days = Column(Integer)
    
    # By Stage
    avg_stage_durations = Column(JSON, default=dict)  # {prospecting: 5, qualification: 8, ...}
    stage_conversion_rates = Column(JSON, default=dict)  # % that move to next stage
    stage_dropout_rates = Column(JSON, default=dict)  # % that fall out
    
    # Velocity
    deals_started = Column(Integer)
    deals_closed = Column(Integer)
    deals_lost = Column(Integer)
    avg_deals_in_pipeline = Column(Float)
    
    # Relationships
    user = relationship("User", back_populates="sales_cycle_metrics")
    
    created_at = Column(DateTime, default=datetime.utcnow)

class ForecastAccuracy(Base):
    __tablename__ = "forecast_accuracy"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Forecast Period
    forecast_month = Column(String)  # YYYY-MM
    forecast_date = Column(DateTime)  # When forecast was made
    
    # Forecast vs Actual
    forecasted_revenue = Column(Float)  # What we predicted
    actual_revenue = Column(Float)  # What we closed
    forecast_accuracy_pct = Column(Float)  # (Actual / Forecasted) * 100
    
    # Breakdown
    by_rep = Column(JSON, default=dict)  # {rep_id: {forecast, actual, accuracy}}
    by_product = Column(JSON, default=dict)
    by_region = Column(JSON, default=dict)
    
    # Analysis
    variance_reasons = Column(JSON, default=list)  # Why was forecast off?
    improvements_needed = Column(Text)
    
    # Win Rate
    win_rate_pct = Column(Float)  # % of deals closed
    deals_forecast = Column(Integer)
    deals_won = Column(Integer)
    deals_lost = Column(Integer)
    
    # Relationships
    user = relationship("User", back_populates="forecast_accuracies")
    
    created_at = Column(DateTime, default=datetime.utcnow)

class TerritoryMetrics(Base):
    __tablename__ = "territory_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Territory Definition
    territory_name = Column(String)  # Region, account list, etc.
    territory_type = Column(String)  # geographic, account-based, product-based
    
    # Performance
    revenue_target = Column(Float)
    revenue_actual = Column(Float)
    revenue_variance_pct = Column(Float)
    
    # Activity
    total_contacts = Column(Integer)
    active_contacts = Column(Integer)  # With recent interaction
    engaged_pct = Column(Float)  # % engaged
    
    # Pipeline
    pipeline_value = Column(Float)
    avg_deal_size = Column(Float)
    deal_count = Column(Integer)
    
    # Health
    win_rate_pct = Column(Float)
    avg_sales_cycle_days = Column(Float)
    quota_attainment_pct = Column(Float)
    
    # Optimization
    growth_rate_pct = Column(Float)  # Period-over-period growth
    opportunity_score = Column(Float)  # 0-100: territory potential
    risk_score = Column(Float)  # 0-100: at-risk deals
    
    # Period
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="territory_metrics")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Update User relationships to include Phase 7 models
User.win_loss_analyses = relationship("WinLossAnalysis", back_populates="user", cascade="all, delete-orphan")
User.sales_cycle_metrics = relationship("SalesCycleMetrics", back_populates="user", cascade="all, delete-orphan")
User.forecast_accuracies = relationship("ForecastAccuracy", back_populates="user", cascade="all, delete-orphan")
User.territory_metrics = relationship("TerritoryMetrics", back_populates="user", cascade="all, delete-orphan")

# Update Deal relationships to include Phase 7 models
Deal.win_loss = relationship("WinLossAnalysis", back_populates="deal", uselist=False, cascade="all, delete-orphan")

# Ensure other models in the codebase are imported and registered on the declarative base
try:
    import models.crm
except ImportError:
    pass

try:
    import models.campaigns
except ImportError:
    pass

# Deduplicate duplicate index objects registered in Base.metadata (caused by multiple classes defining same tables)
for table in Base.metadata.tables.values():
    seen = set()
    dupes = set()
    for idx in list(table.indexes):
        if idx.name in seen:
            dupes.add(idx)
        else:
            seen.add(idx.name)
    table.indexes -= dupes
