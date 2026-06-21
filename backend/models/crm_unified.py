"""
Canonical CRM model exports.
All services should import CRM entities from here instead of auth.models.
"""
from models.crm import (
    Activity,
    AIInsight,
    Campaign,
    CampaignRecipient,
    Contact,
    CustomerProfile,
    Deal,
    DealActivity,
    EmailMetadata,
    GmailSyncCursor,
    Interaction,
    Lead,
    Note,
    TaskRecord,
)

__all__ = [
    "Activity",
    "AIInsight",
    "Campaign",
    "CampaignRecipient",
    "Contact",
    "CustomerProfile",
    "Deal",
    "DealActivity",
    "EmailMetadata",
    "GmailSyncCursor",
    "Interaction",
    "Lead",
    "Note",
    "TaskRecord",
]
