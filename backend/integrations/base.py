"""
P6 — Integration Provider Abstract Base Class
Provider-neutral architecture for external service integrations (Google, Slack, Microsoft, etc.).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IntegrationProvider(ABC):
    """
    Abstract contract for OAuth and third-party API integrations.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier string e.g. 'google', 'slack'."""
        pass

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Builds OAuth2 authorization URL."""
        pass

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchanges authorization code for tokens.
        Returns:
            {
                "access_token": str,
                "refresh_token": Optional[str],
                "expires_in": int,
                "account_identifier": str,
                "scopes": List[str],
                "metadata": dict
            }
        """
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refreshes an expired access token.
        Returns:
            {
                "access_token": str,
                "expires_in": int
            }
        """
        pass

    @abstractmethod
    def revoke_token(self, token: str) -> bool:
        """Revokes an active OAuth access or refresh token."""
        pass

    @abstractmethod
    def get_account_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetches account identity and profile metadata."""
        pass
