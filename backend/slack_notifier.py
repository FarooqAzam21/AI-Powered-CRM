import requests
import os
from logger import setup_logger

log = setup_logger("slack_notifier")

def send_slack_alert(message):
    """
    Send alert to Slack via webhook.
    Webhook URL must be set in SLACK_WEBHOOK_URL environment variable.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not webhook_url:
        log.warning("[SLACK] SLACK_WEBHOOK_URL not configured, skipping alert")
        return False
    
    try:
        payload = {"text": message}
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        log.info(f"[SLACK] Alert sent: {message[:50]}...")
        return True
    except Exception as e:
        log.error(f"[SLACK] Failed to send alert: {e}")
        return False
