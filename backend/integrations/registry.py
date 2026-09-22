"""
P6 — Integration Registry & Secure Storage Manager
Handles registration of IntegrationProvider instances and securely stores
encrypted tokens into the IntegrationConnection database model.
"""
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from integrations.base import IntegrationProvider
from integrations.google_provider import GoogleIntegrationProvider
from models.developer import IntegrationConnection
from utils.security import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    _providers: Dict[str, IntegrationProvider] = {}

    @classmethod
    def register(cls, provider: IntegrationProvider):
        cls._providers[provider.provider_name.lower()] = provider

    @classmethod
    def get(cls, provider_name: str) -> Optional[IntegrationProvider]:
        return cls._providers.get(provider_name.lower())

    @classmethod
    def list_available(cls) -> List[Dict[str, str]]:
        return [
            {"id": "google", "name": "Google / Gmail", "description": "Bi-directional email sync and Google workspace integration", "configured": True},
            {"id": "slack", "name": "Slack", "description": "Channel notifications and CRM bot integration", "configured": False},
            {"id": "microsoft", "name": "Microsoft 365 / Outlook", "description": "Outlook calendar and email sync", "configured": False},
        ]


# Register standard Google provider
IntegrationRegistry.register(GoogleIntegrationProvider())


class IntegrationManager:

    @staticmethod
    def save_connection(
        *,
        db: Session,
        organization_id: int,
        workspace_id: int,
        user_id: int,
        provider: str,
        account_identifier: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int = 3600,
        scopes: List[str] = [],
        metadata: dict = {},
    ) -> IntegrationConnection:
        """
        Encrypts tokens at rest and saves/updates IntegrationConnection.
        """
        conn = (
            db.query(IntegrationConnection)
            .filter(
                IntegrationConnection.workspace_id == workspace_id,
                IntegrationConnection.provider == provider.lower(),
                IntegrationConnection.account_identifier == account_identifier,
            )
            .first()
        )

        enc_access = encrypt_secret(access_token) if access_token else None
        enc_refresh = encrypt_secret(refresh_token) if refresh_token else None
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None

        if not conn:
            conn = IntegrationConnection(
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider.lower(),
                account_identifier=account_identifier,
                encrypted_access_token=enc_access,
                encrypted_refresh_token=enc_refresh,
                token_expires_at=token_expires_at,
                scopes=scopes,
                status="active",
                metadata_json=metadata,
                created_at=datetime.utcnow(),
            )
            db.add(conn)
        else:
            conn.encrypted_access_token = enc_access
            if enc_refresh:
                conn.encrypted_refresh_token = enc_refresh
            conn.token_expires_at = token_expires_at
            conn.scopes = scopes
            conn.metadata_json = metadata
            conn.status = "active"
            conn.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(conn)
        return conn

    @staticmethod
    def get_decrypted_tokens(connection: IntegrationConnection) -> Dict[str, Optional[str]]:
        access = decrypt_secret(connection.encrypted_access_token) if connection.encrypted_access_token else None
        refresh = decrypt_secret(connection.encrypted_refresh_token) if connection.encrypted_refresh_token else None
        return {"access_token": access, "refresh_token": refresh}
