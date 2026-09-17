from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


class Plan(Base):
    __tablename__ = "billing_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    price_monthly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)
    limits = Column(JSON, default=dict)
    features = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)
    trial_days = Column(Integer, default=14)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "billing_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, unique=True, index=True
    )
    plan_id = Column(Integer, ForeignKey("billing_plans.id"), nullable=False)
    status = Column(
        String, default="trial", index=True
    )  # trial, active, past_due, canceled, expired, suspended
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    provider_customer_id = Column(String, nullable=True)
    provider_subscription_id = Column(String, nullable=True)
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan = relationship("Plan", back_populates="subscriptions")
    organization = relationship("Organization")


class SubscriptionHistory(Base):
    __tablename__ = "billing_subscription_history"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    subscription_id = Column(
        Integer, ForeignKey("billing_subscriptions.id"), nullable=True
    )
    event_type = Column(String, nullable=False)
    from_plan_id = Column(Integer, nullable=True)
    to_plan_id = Column(Integer, nullable=True)
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageCounter(Base):
    __tablename__ = "billing_usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "resource", "period_key", name="uq_org_resource_period"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    resource = Column(String, nullable=False, index=True)
    count = Column(Integer, default=0)
    period_key = Column(String, default="total", index=True)
    last_reset_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="processed")
