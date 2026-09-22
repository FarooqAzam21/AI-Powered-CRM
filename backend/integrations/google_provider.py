"""
P6 — Google Integration Provider
Adapts existing Google OAuth / Gmail integration into the standard IntegrationProvider interface.
"""
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import requests

from integrations.base import IntegrationProvider
from config.settings import get_settings

logger = logging.getLogger(__name__)


class GoogleIntegrationProvider(IntegrationProvider):

    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.google_client_id
        self.client_secret = self.settings.google_client_secret

    @property
    def provider_name(self) -> str:
        return "google"

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        scope = (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send"
        )
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        resp = requests.post(token_url, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()

        access_token = token_data.get("access_token")
        profile = self.get_account_profile(access_token) if access_token else {}

        return {
            "access_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", 3600),
            "account_identifier": profile.get("email", ""),
            "scopes": token_data.get("scope", "").split(),
            "metadata": profile,
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        resp = requests.post(token_url, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
        return {
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in", 3600),
        }

    def revoke_token(self, token: str) -> bool:
        revoke_url = f"https://oauth2.googleapis.com/revoke?token={token}"
        try:
            resp = requests.post(revoke_url, timeout=5)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Failed to revoke Google token: %s", exc)
            return False

    def get_account_profile(self, access_token: str) -> Dict[str, Any]:
        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            if resp.ok:
                return resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch Google profile: %s", exc)
        return {}
