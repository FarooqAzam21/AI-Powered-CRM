import time
from datetime import datetime

from auth.models import User
from config.settings import get_settings
from database import SessionLocal
from gmail_service import send_gmail_message
from models.crm import Campaign, CampaignRecipient
from tasks.celery_app import celery_app
from tasks.task_status import update_task
from utils.sanitize import sanitize_email_html


def _send_campaign(task_id, payload):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == payload["campaign_id"]).first()
        if not campaign:
            raise ValueError("Campaign not found")
        user = db.query(User).filter(User.id == campaign.user_id).first()
        if not user or not user.gmail_connected:
            raise ValueError("Gmail not connected for campaign owner")

        recipients = (
            db.query(CampaignRecipient)
            .filter(CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.status == "queued")
            .all()
        )
        delay = 60 / max(campaign.throttle_per_minute or get_settings().campaign_send_rate_per_minute, 1)
        campaign.status = "running"
        db.commit()
        total = max(len(recipients), 1)

        for index, recipient in enumerate(recipients, start=1):
            body = sanitize_email_html(campaign.template.replace("{{email}}", recipient.email))
            subject = campaign.subject
            result = send_gmail_message(user, recipient.email, subject, body)
            if result:
                recipient.status = "sent"
                recipient.sent_at = datetime.utcnow()
                campaign.sent_count += 1
            else:
                recipient.status = "failed"
                recipient.last_error = "Gmail API send failed"
            db.commit()
            update_task(
                task_id,
                status="running",
                progress=round(index / total * 100),
                result={"sent": campaign.sent_count, "failed": index - campaign.sent_count},
            )
            if index < len(recipients):
                time.sleep(delay)

        campaign.status = "completed" if campaign.sent_count else "failed"
        db.commit()
        update_task(task_id, status="completed", progress=100, result={"sent": campaign.sent_count})
        return {"sent": campaign.sent_count}
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


if celery_app:
    send_campaign = celery_app.task(name="workers.campaign_tasks.send_campaign")(_send_campaign)
else:
    send_campaign = _send_campaign
