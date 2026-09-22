from auth.models import Email, Notification, User
from models.crm import (
    AIInsight,
    Activity,
    Campaign,
    CampaignRecipient,
    Contact,
    Deal,
    EmailClassificationRule,
    EmailMetadata,
    GmailSyncCursor,
    Interaction,
    Lead,
    Note,
    TaskRecord,
)
from models.ai_copilot import (
    AIConversation,
    AIMessage,
    RAGDocument,
    AIAuditLog,
)
from models.workflow import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowApproval,
    WorkflowAuditLog,
)
from models.developer import (
    DeveloperAPIKey,
    WebhookEndpoint,
    WebhookDeliveryRecord,
    IntegrationConnection,
    PublicAPILog,
)

__all__ = [
    "User",
    "Email",
    "Notification",
    "Contact",
    "Lead",
    "Activity",
    "Interaction",
    "Note",
    "Campaign",
    "CampaignRecipient",
    "Deal",
    "EmailClassificationRule",
    "AIInsight",
    "EmailMetadata",
    "GmailSyncCursor",
    "TaskRecord",
    "AIConversation",
    "AIMessage",
    "RAGDocument",
    "AIAuditLog",
    # P5 — Workflow Automation
    "Workflow",
    "WorkflowExecution",
    "WorkflowExecutionStep",
    "WorkflowApproval",
    "WorkflowAuditLog",
    # P6 — Developer Platform
    "DeveloperAPIKey",
    "WebhookEndpoint",
    "WebhookDeliveryRecord",
    "IntegrationConnection",
    "PublicAPILog",
]
