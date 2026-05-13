import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Test Slack webhook (if configured)
webhook_url = os.getenv("SLACK_WEBHOOK_URL")
if webhook_url:
    try:
        requests.post(
            webhook_url,
            json={
                "text": "🚀 Slack app connected successfully!"
            },
            timeout=5
        )
        print("✓ Slack webhook test successful")
    except Exception as e:
        print(f"✗ Slack webhook test failed: {e}")
else:
    print("⚠ SLACK_WEBHOOK_URL not configured, skipping Slack test")