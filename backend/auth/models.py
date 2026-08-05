from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

# =================== WORKSPACES & AUTH ===================
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    settings = relationship("OrganizationSettings", back_populates="organization", uselist=False, cascade="all, delete-orphan")


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True, index=True)
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")
    currency = Column(String, default="USD")
    date_format = Column(String, default="YYYY-MM-DD")
    theme = Column(String, default="light")
    password_policy = Column(JSON, default=dict)
    session_timeout_minutes = Column(Integer, default=60)
    mfa_required = Column(Boolean, default=False)
    notification_preferences = Column(JSON, default=dict)
    security_policies = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="settings")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, index=True, nullable=True)
    type = Column(String, default="Team")  # Personal, Team, Enterprise
    storage_quota_mb = Column(Integer, default=5000)
    ai_monthly_quota = Column(Integer, default=10000)
    brand_logo = Column(String, nullable=True)
    brand_color = Column(String, default="#6366f1")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="workspaces")
    users = relationship("User", back_populates="workspace", cascade="all, delete-orphan")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="workspace", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="workspace", cascade="all, delete-orphan")
    invitations = relationship("WorkspaceInvitation", back_populates="workspace", cascade="all, delete-orphan")
    settings = relationship("WorkspaceSetting", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    quota = relationship("WorkspaceQuota", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    usage = relationship("WorkspaceUsage", back_populates="workspace", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="departments")
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    name = Column(String, nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="teams")
    department = relationship("Department", back_populates="teams")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="Viewer")
    status = Column(String, default="active")
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_members")

    __table_args__ = ({"extend_existing": True},)


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String, nullable=False, index=True)
    role = Column(String, default="Viewer")
    token = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending")  # pending, accepted, expired, canceled
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    workspace = relationship("Workspace", back_populates="invitations")


class WorkspaceSetting(Base):
    __tablename__ = "workspace_settings"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    ai_provider = Column(String, default="ollama")
    ai_model = Column(String, default="qwen2.5:1.5b")
    smtp_host = Column(String, nullable=True)
    smtp_port = Column(Integer, nullable=True)
    timezone = Column(String, default="UTC")
    language = Column(String, default="en")
    currency = Column(String, default="USD")
    date_format = Column(String, default="YYYY-MM-DD")
    theme = Column(String, default="light")
    password_policy = Column(JSON, default=dict)
    session_timeout_minutes = Column(Integer, default=60)
    mfa_required = Column(Boolean, default=False)
    notification_preferences = Column(JSON, default=dict)
    security_policies = Column(JSON, default=dict)
    feature_flags = Column(JSON, default=dict)
    custom_domain = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="settings")


class WorkspaceQuota(Base):
    __tablename__ = "workspace_quotas"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    emails_synced = Column(Integer, default=0)
    ai_requests = Column(Integer, default=0)
    storage_used_mb = Column(Integer, default=0)
    knowledge_base_size_mb = Column(Integer, default=0)
    campaign_emails = Column(Integer, default=0)
    api_requests = Column(Integer, default=0)
    webhook_deliveries = Column(Integer, default=0)
    workflow_runs = Column(Integer, default=0)
    agent_executions = Column(Integer, default=0)
    users_count = Column(Integer, default=0)
    teams_count = Column(Integer, default=0)
    departments_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="quota")


class WorkspaceUsage(Base):
    __tablename__ = "workspace_usage"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=True, index=True)
    period_end = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    workspace = relationship("Workspace", back_populates="usage")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    key = Column(String, unique=True, index=True, nullable=True) # plaintext legacy key
    hashed_key = Column(String, unique=True, index=True, nullable=True)
    key_prefix = Column(String, nullable=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(String, default="active") # active, revoked, expired
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    last_ip = Column(String, nullable=True)
    permissions = Column(JSON, default=list) # scopes list, e.g. ["contacts.read"]
    rate_limit = Column(Integer, default=60) # per minute
    daily_limit = Column(Integer, default=1000) # per day
    requests_today = Column(Integer, default=0)
    description = Column(String, nullable=True)

    workspace = relationship("Workspace", back_populates="api_keys")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    status = Column(String, nullable=False) # e.g., "DENIED", "ALLOWED"
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="Viewer") # Super Admin, Workspace Admin, Security Analyst, Viewer
    job_title = Column(String, nullable=True)
    status = Column(String, default="active") # active, deactivated, suspended
    
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)

    workspace_members = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], back_populates="users")


class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkspacePolicy(Base):
    __tablename__ = "workspace_policies"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False)  # e.g., security, data_retention, ai_usage
    rules = Column(JSON, default=dict)
    is_enforced = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Google OAuth
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    gmail_connected = Column(Boolean, default=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="users")
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
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

# =================== DEVELOPER & WEBHOOKS ===================
class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    url = Column(String, nullable=False)
    secret_key = Column(String, nullable=False)
    events = Column(JSON, default=list) # e.g., ["lead.created"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id"), nullable=False)
    event = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    status = Column(String, default="failed") # success, failed
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

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
