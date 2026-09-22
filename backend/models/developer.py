"""
P6 — Developer Platform Models
API Keys, Webhooks, Integrations, and Public API request logging.
All models are strictly workspace- and organization-scoped.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime,
    ForeignKey, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from database import Base


class DeveloperAPIKey(Base):
    """
    Organization and Workspace-scoped API Keys.
    Stores SHA-256 hash of the secret key. Never stores raw key.
    """
    __tablename__ = "developer_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    name = Column(String(255), nullable=False)
    key_prefix = Column(String(32), nullable=False, index=True)  # e.g., "crm_live_abc12"
    hashed_key = Column(String(128), nullable=False, unique=True, index=True)

    # Scopes list: ["contacts:read", "contacts:write", "deals:read", etc.]
    scopes = Column(JSON, default=list, nullable=False)

    # active | revoked | expired
    status = Column(String(32), default="active", nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    rate_limit = Column(Integer, default=60)      # requests per minute
    daily_limit = Column(Integer, default=1000)   # requests per day
    description = Column(Text, nullable=True)

    last_used_at = Column(DateTime, nullable=True)
    last_ip = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_dev_apikey_org_ws", "organization_id", "workspace_id"),
        Index("idx_dev_apikey_lookup", "key_prefix", "status"),
    )


class WebhookEndpoint(Base):
    """
    Outbound webhook subscription endpoints registered by developers.
    """
    __tablename__ = "developer_webhook_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    # HMAC-SHA256 signing secret: "whsec_..."
    secret_key = Column(String(128), nullable=False)

    # List of subscribed events e.g. ["contact.created", "deal.stage_changed"] or ["*"]
    events = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deliveries = relationship("WebhookDeliveryRecord", back_populates="endpoint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dev_webhook_org_ws", "organization_id", "workspace_id"),
    )


class WebhookDeliveryRecord(Base):
    """
    Tracks individual delivery attempts for a webhook event.
    """
    __tablename__ = "developer_webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("developer_webhook_endpoints.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False, index=True)
    event_id = Column(String(64), nullable=False, index=True)  # UUID for deduplication

    # Sanitized payload
    payload = Column(JSON, default=dict, nullable=False)

    # pending | success | failed | retrying
    status = Column(String(32), default="pending", nullable=False, index=True)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    next_retry_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")

    __table_args__ = (
        Index("idx_dev_wh_delivery_status", "status", "next_retry_at"),
        Index("idx_dev_wh_delivery_lookup", "endpoint_id", "event_id"),
    )


class IntegrationConnection(Base):
    """
    Stores connected third-party integration accounts (e.g., Google/Gmail, Slack).
    Sensitive tokens are encrypted at rest.
    """
    __tablename__ = "developer_integrations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String(64), nullable=False, index=True)  # "google", "slack", "microsoft"
    account_identifier = Column(String(255), nullable=True)   # e.g., email or account ID

    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    scopes = Column(JSON, default=list, nullable=False)
    # active | revoked | expired | error
    status = Column(String(32), default="active", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", "account_identifier", name="uq_dev_integration_account"),
        Index("idx_dev_integration_ws_provider", "workspace_id", "provider"),
    )


class PublicAPILog(Base):
    """
    High-performance audit logging for public API requests.
    """
    __tablename__ = "developer_api_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("developer_api_keys.id"), nullable=True, index=True)

    method = Column(String(16), nullable=False)
    endpoint = Column(String(255), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_dev_api_logs_org_ws", "organization_id", "workspace_id", "timestamp"),
    )
