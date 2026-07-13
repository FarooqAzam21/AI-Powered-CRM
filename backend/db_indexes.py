import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


INDEXES = [
    (
        "ix_email_meta_user_date",
        "CREATE INDEX IF NOT EXISTS ix_email_meta_user_date ON email_metadata (user_id, internal_date DESC)",
    ),
    (
        "ix_email_meta_user_sender",
        "CREATE INDEX IF NOT EXISTS ix_email_meta_user_sender ON email_metadata (user_id, sender_email)",
    ),
    (
        "ix_email_meta_user_status",
        "CREATE INDEX IF NOT EXISTS ix_email_meta_user_status ON email_metadata (user_id, ai_status)",
    ),
    (
        "ix_crm_contacts_user_last_interaction",
        "CREATE INDEX IF NOT EXISTS ix_crm_contacts_user_last_interaction ON crm_contacts (user_id, last_interaction_at DESC)",
    ),
    (
        "ix_crm_leads_user_label_score",
        "CREATE INDEX IF NOT EXISTS ix_crm_leads_user_label_score ON crm_leads (user_id, label, score DESC)",
    ),
    (
        "ix_campaign_recipients_campaign_status",
        "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_campaign_status ON campaign_recipients (campaign_id, status)",
    ),
]


def ensure_performance_indexes(engine):
    with engine.begin() as conn:
        for name, statement in INDEXES:
            try:
                conn.execute(text(statement))
            except Exception as exc:
                logger.warning("Index %s could not be created: %s", name, exc)
