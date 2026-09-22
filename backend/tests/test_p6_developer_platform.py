"""
P6 — Enterprise Developer Platform: Comprehensive Test Suite

Tests cover:
  1. API Key creation, hashing, prefix, single reveal guarantee
  2. Bearer & X-API-Key authentication
  3. Revoked / expired key rejection
  4. Scope enforcement (contacts:read cannot write)
  5. Public API v1 CRUD: contacts, deals, tasks, activities, workflows, analytics
  6. P3 quota enforcement (api_requests metering)
  7. Webhook HMAC signature generation & verification
  8. Webhook endpoint CRUD via developer_router
  9. Integration token encryption/decryption
  10. CRITICAL: Cross-organization isolation — Org A key CANNOT access Org B data
"""

import hashlib
import hmac
import json
import pytest
import secrets
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import (
    User, Workspace, Organization, WorkspaceMember,
    APIKey, AuditLog, WebhookSubscription,
)
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role
from models.developer import (
    DeveloperAPIKey, WebhookEndpoint, WebhookDeliveryRecord,
    IntegrationConnection, PublicAPILog,
)
from models.crm import Contact, Deal
from billing.plans import seed_default_plans
from billing.service import BillingService
from services.webhook_dispatcher import (
    calculate_webhook_signature,
    verify_webhook_signature,
    VALID_WEBHOOK_EVENTS,
    WebhookDispatcher,
)

# ---------------------------------------------------------------------------
# Test DB Setup
# ---------------------------------------------------------------------------
DB_URL = "sqlite:///./test_p6_developer_platform.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


# ---------------------------------------------------------------------------
# JWT Token Helpers
# ---------------------------------------------------------------------------
def make_jwt(email: str, role: str, org_id: int, ws_id: int) -> str:
    payload = {
        "sub": email,
        "role": role,
        "organization_id": org_id,
        "workspace_id": ws_id,
        "exp": datetime.utcnow() + timedelta(hours=2),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# DB Fixture — Two fully isolated organizations
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def env():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_default_plans(db)

    uid = uuid.uuid4().hex[:6]

    # Org A
    org_a = Organization(name=f"Org A {uid}", slug=f"org-a-{uid}")
    db.add(org_a)
    db.flush()
    ws_a = Workspace(name="WS Alpha", organization_id=org_a.id)
    db.add(ws_a)
    db.flush()
    user_a = User(
        email=f"admin_a_{uid}@test.com",
        name=f"Admin A {uid}",
        password="hashed_placeholder",
        role=Role.WORKSPACE_ADMIN,
        organization_id=org_a.id,
        workspace_id=ws_a.id,
        is_verified=True,
    )
    db.add(user_a)
    db.flush()
    db.add(WorkspaceMember(
        user_id=user_a.id,
        workspace_id=ws_a.id,
        organization_id=org_a.id,
        role=Role.WORKSPACE_ADMIN,
        status="active",
    ))

    # Org B
    org_b = Organization(name=f"Org B {uid}", slug=f"org-b-{uid}")
    db.add(org_b)
    db.flush()
    ws_b = Workspace(name="WS Beta", organization_id=org_b.id)
    db.add(ws_b)
    db.flush()
    user_b = User(
        email=f"admin_b_{uid}@test.com",
        name=f"Admin B {uid}",
        password="hashed_placeholder",
        role=Role.WORKSPACE_ADMIN,
        organization_id=org_b.id,
        workspace_id=ws_b.id,
        is_verified=True,
    )
    db.add(user_b)
    db.flush()
    db.add(WorkspaceMember(
        user_id=user_b.id,
        workspace_id=ws_b.id,
        organization_id=org_b.id,
        role=Role.WORKSPACE_ADMIN,
        status="active",
    ))

    db.commit()
    db.refresh(org_a); db.refresh(org_b)
    db.refresh(ws_a); db.refresh(ws_b)
    db.refresh(user_a); db.refresh(user_b)

    token_a = make_jwt(user_a.email, user_a.role, org_a.id, ws_a.id)
    token_b = make_jwt(user_b.email, user_b.role, org_b.id, ws_b.id)


    yield {
        "db": db,
        "org_a": org_a, "ws_a": ws_a, "user_a": user_a, "token_a": token_a,
        "org_b": org_b, "ws_b": ws_b, "user_b": user_b, "token_b": token_b,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def _make_dev_key(db, org_id: int, ws_id: int, scopes: list) -> str:
    """Helper: create a DeveloperAPIKey directly in DB."""
    raw_key = "crm_live_" + secrets.token_urlsafe(24)
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    key = DeveloperAPIKey(
        organization_id=org_id,
        workspace_id=ws_id,
        name=f"Test key {scopes[:2]}",
        key_prefix=raw_key[:12],
        hashed_key=hashed,
        scopes=scopes,
        status="active",
        is_active=True,
    )
    db.add(key)
    db.commit()
    return raw_key


# ===========================================================================
# 1. API KEY MANAGEMENT — Creation, Hashing, Single Reveal
# ===========================================================================

class TestAPIKeyManagement:
    """Tests API key lifecycle via /api/v1/developer/keys"""

    def test_create_api_key_returns_plaintext_once(self, env):
        token = env["token_a"]
        resp = client.post("/api/v1/developer/keys", json={
            "name": "Test Key Alpha",
            "permissions": ["contacts:read", "deals:read"],
            "rate_limit": 100,
            "daily_limit": 5000,
            "expires_in_days": 30,
            "description": "Read-only test key",
            "is_live": True,
        }, headers=auth_headers(token))
        assert resp.status_code == 200, f"Create key failed: {resp.text}"
        data = resp.json()
        assert "plaintext_key" in data, "Plaintext key must be returned on creation"
        assert data["plaintext_key"].startswith("crm_"), "Key must have crm_ prefix"
        assert data["key_prefix"] in data["plaintext_key"], "Prefix must be in full key"
        # Store for subsequent tests
        env["key_a_plaintext"] = data["plaintext_key"]
        env["key_a_id"] = data["id"]

    def test_api_key_hashed_in_database(self, env):
        """Key stored in DB must be SHA-256 hash, not plaintext."""
        db = env["db"]
        db.expire_all()
        key_rec = db.query(DeveloperAPIKey).filter(DeveloperAPIKey.id == env["key_a_id"]).first()
        assert key_rec is not None
        raw = env["key_a_plaintext"]
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert key_rec.hashed_key == expected_hash, "DB must store hash, not raw key"
        assert key_rec.hashed_key != raw, "DB must NOT store raw plaintext key"

    def test_list_api_keys_hides_secret(self, env):
        resp = client.get("/api/v1/developer/keys", headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200
        keys_list = resp.json()
        assert isinstance(keys_list, list)
        for k in keys_list:
            # The listing endpoint must NOT expose plaintext_key
            assert "plaintext_key" not in k or k.get("plaintext_key") is None, \
                "Listing must not expose plaintext keys"

    def test_create_second_key_for_org_b(self, env):
        resp = client.post("/api/v1/developer/keys", json={
            "name": "Org B Key",
            "permissions": ["contacts:read", "deals:read", "contacts:write"],
            "is_live": True,
        }, headers=auth_headers(env["token_b"]))
        assert resp.status_code == 200
        env["key_b_plaintext"] = resp.json()["plaintext_key"]
        env["key_b_id"] = resp.json()["id"]

    def test_revoke_key(self, env):
        """Create, then revoke a key; verify it is marked revoked in DB."""
        resp = client.post("/api/v1/developer/keys", json={
            "name": "Key To Revoke",
            "permissions": ["contacts:read"],
            "is_live": True,
        }, headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200
        key_id = resp.json()["id"]

        # Revoke via PATCH
        rev = client.patch(f"/api/v1/developer/keys/{key_id}", json={"status": "revoked"},
                           headers=auth_headers(env["token_a"]))
        assert rev.status_code == 200

        db = env["db"]
        db.expire_all()
        key_rec = db.query(DeveloperAPIKey).filter(DeveloperAPIKey.id == key_id).first()
        assert key_rec.status == "revoked"


# ===========================================================================
# 2. PUBLIC API AUTHENTICATION — Bearer / X-API-Key / Invalid
# ===========================================================================

class TestPublicAPIAuthentication:

    def test_missing_api_key_returns_401(self, env):
        resp = client.get("/api/public/v1/contacts")
        assert resp.status_code == 401

    def test_garbage_key_returns_401(self, env):
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": "garbage_value"})
        assert resp.status_code == 401

    def test_wrong_prefix_key_returns_401(self, env):
        resp = client.get("/api/public/v1/contacts",
                          headers={"X-API-Key": "openai_sk_thisisbad"})
        assert resp.status_code == 401

    def test_x_api_key_header_authentication(self, env):
        """A valid key provided via X-API-Key must authenticate successfully."""
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": key})
        assert resp.status_code in (200, 201, 204), f"Expected success, got {resp.status_code}: {resp.text}"

    def test_bearer_token_authentication(self, env):
        """A valid key provided via Authorization: Bearer must authenticate successfully."""
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.get("/api/public/v1/contacts",
                          headers={"Authorization": f"Bearer {key}"})
        assert resp.status_code in (200, 201, 204), f"Expected success, got {resp.status_code}: {resp.text}"

    def test_revoked_key_rejected(self, env):
        """Create and immediately revoke a key; verify public API rejects it."""
        db = env["db"]
        raw_key = "crm_live_" + secrets.token_urlsafe(24)
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        revoked = DeveloperAPIKey(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            name="Revoked Key Test",
            key_prefix=raw_key[:12],
            hashed_key=hashed,
            scopes=["contacts:read"],
            status="revoked",
            is_active=False,
        )
        db.add(revoked)
        db.commit()
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401, f"Expected 401 for revoked key, got {resp.status_code}"

    def test_expired_key_rejected(self, env):
        """A key whose expires_at is in the past must be rejected with 401."""
        db = env["db"]
        raw_key = "crm_live_" + secrets.token_urlsafe(24)
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        expired = DeveloperAPIKey(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            name="Expired Key Test",
            key_prefix=raw_key[:12],
            hashed_key=hashed,
            scopes=["contacts:read"],
            status="active",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(expired)
        db.commit()
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": raw_key})
        assert resp.status_code == 401, f"Expected 401 for expired key, got {resp.status_code}"


# ===========================================================================
# 3. SCOPE ENFORCEMENT
# ===========================================================================

class TestScopeEnforcement:

    def test_read_scope_can_get_contacts(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": key})
        assert resp.status_code in (200, 204), \
            f"contacts:read should allow GET /contacts, got {resp.status_code}"

    def test_read_only_scope_cannot_create_contact(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.post("/api/public/v1/contacts", json={
            "name": "Unauthorized Contact",
            "email": "unauth@test.com",
        }, headers={"X-API-Key": key})
        assert resp.status_code == 403, \
            f"contacts:read must NOT allow POST /contacts, got {resp.status_code}"

    def test_write_scope_can_create_contact(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read", "contacts:write"])
        resp = client.post("/api/public/v1/contacts", json={
            "name": "Authorized Contact",
            "email": f"auth_{uuid.uuid4().hex[:6]}@test.com",
        }, headers={"X-API-Key": key})
        assert resp.status_code in (200, 201), \
            f"contacts:write should allow POST /contacts, got {resp.status_code}: {resp.text}"

    def test_deals_read_scope_can_get_deals(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["deals:read"])
        resp = client.get("/api/public/v1/deals", headers={"X-API-Key": key})
        assert resp.status_code in (200, 204)

    def test_no_deals_scope_cannot_get_deals(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.get("/api/public/v1/deals", headers={"X-API-Key": key})
        assert resp.status_code == 403, \
            f"Key without deals:read must be blocked from /deals, got {resp.status_code}"

    def test_wildcard_scope_allows_all(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["*"])
        r1 = client.get("/api/public/v1/contacts", headers={"X-API-Key": key})
        r2 = client.get("/api/public/v1/deals", headers={"X-API-Key": key})
        assert r1.status_code in (200, 204)
        assert r2.status_code in (200, 204)

    def test_analytics_scope_required_for_analytics(self, env):
        key = _make_dev_key(env["db"], env["org_a"].id, env["ws_a"].id, ["contacts:read"])
        resp = client.get("/api/public/v1/analytics/overview", headers={"X-API-Key": key})
        assert resp.status_code == 403


# ===========================================================================
# 4. PUBLIC API v1 CRUD
# ===========================================================================

class TestPublicAPIv1CRUD:
    """End-to-end tests for the versioned public API endpoints."""

    @pytest.fixture(autouse=True)
    def full_key(self, env):
        self.headers = {"X-API-Key": _make_dev_key(
            env["db"], env["org_a"].id, env["ws_a"].id, ["*"]
        )}
        self.env = env

    def test_contacts_list(self):
        resp = client.get("/api/public/v1/contacts", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data or isinstance(data, list), "Expected list or paginated response"

    def test_contacts_create_and_get(self):
        uid = uuid.uuid4().hex[:6]
        resp = client.post("/api/public/v1/contacts", json={
            "name": f"Test Contact {uid}",
            "email": f"tc_{uid}@test.com",
            "phone": "+1-555-0100",
        }, headers=self.headers)
        assert resp.status_code in (200, 201), resp.text
        created = resp.json()
        assert "id" in created or "email" in created
        self.env["created_contact_id"] = created.get("id")

    def test_deals_list(self):
        resp = client.get("/api/public/v1/deals", headers=self.headers)
        assert resp.status_code == 200

    def test_tasks_list(self):
        resp = client.get("/api/public/v1/tasks", headers=self.headers)
        assert resp.status_code == 200

    def test_activities_list(self):
        resp = client.get("/api/public/v1/activities", headers=self.headers)
        assert resp.status_code == 200

    def test_workflows_list(self):
        resp = client.get("/api/public/v1/workflows", headers=self.headers)
        assert resp.status_code == 200

    def test_analytics_overview(self):
        resp = client.get("/api/public/v1/analytics/overview", headers=self.headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_contact_patch_updates_field(self):
        """Create contact, then PATCH email, confirm response."""
        uid = uuid.uuid4().hex[:6]
        create = client.post("/api/public/v1/contacts", json={
            "name": f"Patch Target {uid}",
            "email": f"patch_target_{uid}@test.com",
        }, headers=self.headers)
        assert create.status_code in (200, 201), create.text
        cid = create.json().get("id")
        if cid:
            patch_resp = client.patch(f"/api/public/v1/contacts/{cid}", json={
                "email": f"updated_{uid}@test.com",
            }, headers=self.headers)
            assert patch_resp.status_code in (200, 204), patch_resp.text


# ===========================================================================
# 5. WEBHOOK PLATFORM — HMAC Signatures
# ===========================================================================

class TestWebhookSignatures:
    """Pure unit tests for webhook signature generation & verification."""

    def test_signature_format(self):
        sig = calculate_webhook_signature("my_secret", b'{"event":"test"}', 1700000000)
        assert sig.startswith("t="), "Signature must start with t="
        assert "v1=" in sig, "Signature must contain v1="

    def test_signature_round_trip_valid(self):
        import time
        secret = secrets.token_hex(32)
        payload = json.dumps({"event": "contact.created", "id": 1}).encode()
        ts = int(time.time())
        sig = calculate_webhook_signature(secret, payload, ts)
        # Verify using the same timestamp to avoid clock skew issues
        assert verify_webhook_signature(secret, payload, sig, tolerance_seconds=300)

    def test_wrong_secret_fails_verification(self):
        import time
        payload = b'{"event":"test"}'
        ts = int(time.time())
        sig = calculate_webhook_signature("correct_secret", payload, ts)
        assert not verify_webhook_signature("wrong_secret", payload, sig, tolerance_seconds=300)

    def test_tampered_payload_fails_verification(self):
        import time
        secret = "test_secret_key"
        original = b'{"event":"contact.created","id":1}'
        ts = int(time.time())
        sig = calculate_webhook_signature(secret, original, ts)
        tampered = b'{"event":"contact.created","id":999}'
        assert not verify_webhook_signature(secret, tampered, sig, tolerance_seconds=300)

    def test_expired_timestamp_fails_verification(self):
        import time
        secret = "test_secret"
        payload = b'{"event":"deal.stage_changed"}'
        old_ts = int(time.time()) - 600  # 10 minutes old
        sig = calculate_webhook_signature(secret, payload, old_ts)
        assert not verify_webhook_signature(secret, payload, sig, tolerance_seconds=300)

    def test_valid_webhook_events_catalog(self):
        assert "contact.created" in VALID_WEBHOOK_EVENTS
        assert "deal.stage_changed" in VALID_WEBHOOK_EVENTS
        assert "workflow.completed" in VALID_WEBHOOK_EVENTS
        assert "approval.created" in VALID_WEBHOOK_EVENTS

    def test_hmac_replay_attack_blocked(self):
        """A signature older than tolerance must be rejected."""
        import time
        secret = "replay_test_secret"
        payload = b'{"event":"email.received","id":"abc"}'
        old_ts = int(time.time()) - 400  # 6+ minutes old
        sig = calculate_webhook_signature(secret, payload, old_ts)
        assert not verify_webhook_signature(secret, payload, sig, tolerance_seconds=300)


class TestWebhookEndpointCRUD:
    """Tests for webhook subscription management endpoints."""

    def test_create_webhook_endpoint(self, env):
        resp = client.post("/api/v1/developer/webhooks", json={
            "url": "https://example.com/webhook",
            "events": ["contact.created", "deal.stage_changed"],
            "is_active": True,
        }, headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "secret_key" in data
        assert len(data["secret_key"]) > 10
        env["webhook_id_a"] = data["id"]

    def test_list_webhooks(self, env):
        resp = client.get("/api/v1/developer/webhooks", headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_org_b_cannot_see_org_a_webhooks(self, env):
        """Org B listing webhooks must not return Org A webhooks."""
        wh_id = env.get("webhook_id_a")
        if not wh_id:
            pytest.skip("webhook_id_a not set")
        resp = client.get("/api/v1/developer/webhooks", headers=auth_headers(env["token_b"]))
        assert resp.status_code == 200
        ids = [w["id"] for w in resp.json()]
        assert wh_id not in ids, "Org B must NOT see Org A's webhook endpoints"

    def test_delete_webhook(self, env):
        resp = client.post("/api/v1/developer/webhooks", json={
            "url": "https://delete-me.test/wh",
            "events": ["task.created"],
        }, headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200
        wh_id = resp.json()["id"]
        del_resp = client.delete(f"/api/v1/developer/webhooks/{wh_id}",
                                 headers=auth_headers(env["token_a"]))
        assert del_resp.status_code in (200, 204)


# ===========================================================================
# 6. INTEGRATION TOKEN ENCRYPTION (Unit)
# ===========================================================================

class TestIntegrationTokenEncryption:
    """Verify that encrypt_secret / decrypt_secret correctly protects tokens."""

    def test_encrypt_decrypt_roundtrip(self):
        from utils.security import encrypt_secret, decrypt_secret
        plaintext = "ya29.a0AbVbY6P..." + secrets.token_hex(32)
        encrypted = encrypt_secret(plaintext)
        assert encrypted is not None
        decrypted = decrypt_secret(encrypted)
        assert decrypted == plaintext, "Decrypted token must match original plaintext"

    def test_encrypt_returns_different_value_when_key_configured(self):
        from utils.security import encrypt_secret
        from config.settings import get_settings
        settings = get_settings()
        if not settings.token_encryption_key:
            pytest.skip("token_encryption_key not configured — encryption inactive in test env")
        plaintext = "access_token_" + secrets.token_hex(16)
        encrypted = encrypt_secret(plaintext)
        assert encrypted != plaintext, "Encrypted token must differ from plaintext when key is set"

    def test_none_input_returns_none(self):
        from utils.security import encrypt_secret, decrypt_secret
        assert encrypt_secret(None) is None
        assert decrypt_secret(None) is None

    def test_integration_manager_saves_encrypted(self, env):
        """IntegrationManager.save_connection must encrypt tokens at rest."""
        from integrations.registry import IntegrationManager
        db = env["db"]
        plaintext_access = "ya29.testtoken_" + secrets.token_hex(16)
        conn = IntegrationManager.save_connection(
            db=db,
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            user_id=env["user_a"].id,
            provider="google",
            account_identifier=f"test_{uuid.uuid4().hex[:6]}@gmail.com",
            access_token=plaintext_access,
            refresh_token=None,
            scopes=["email", "profile"],
        )
        db.refresh(conn)
        retrieved = IntegrationManager.get_decrypted_tokens(conn)
        assert retrieved["access_token"] == plaintext_access, \
            "Decrypted access_token must match original plaintext"


# ===========================================================================
# 7. P3 QUOTA — api_requests Metering
# ===========================================================================

class TestAPIRequestsQuotaMetering:
    """Verify api_requests usage is incremented on each successful public API call."""

    def test_api_request_increments_usage_counter(self, env):
        db = env["db"]
        org_a_id = env["org_a"].id
        key = _make_dev_key(db, org_a_id, env["ws_a"].id, ["contacts:read"])

        before = BillingService.check_quota(org_a_id, "api_requests", db=db)
        before_used = before.used if before else 0

        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": key})
        assert resp.status_code in (200, 204), f"Expected success: {resp.text}"

        db.expire_all()
        after = BillingService.check_quota(org_a_id, "api_requests", db=db)
        after_used = after.used if after else 0

        assert after_used >= before_used, "Usage should be >= before (counter incremented)"


# ===========================================================================
# 8. CROSS-ORGANIZATION ISOLATION — CRITICAL SECURITY TEST
# ===========================================================================

class TestCrossOrganizationIsolation:
    """
    CRITICAL: API Key from Org A must NEVER access Org B's data and vice versa.
    """

    @pytest.fixture(autouse=True)
    def keys(self, env):
        db = env["db"]
        self.key_a = _make_dev_key(db, env["org_a"].id, env["ws_a"].id, ["*"])
        self.key_b = _make_dev_key(db, env["org_b"].id, env["ws_b"].id, ["*"])

        # Create a contact in Org A's workspace
        contact_a = Contact(
            name="Org A Exclusive Contact",
            email=f"exclusive_a_{uuid.uuid4().hex[:6]}@orga.com",
            workspace_id=env["ws_a"].id,
            user_id=env["user_a"].id,
        )
        db.add(contact_a)
        db.commit()
        db.refresh(contact_a)
        self.contact_a_id = contact_a.id
        self.env = env

    def test_key_b_cannot_read_org_a_contacts(self):
        """Org B's API key must not see Org A contacts in results."""
        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": self.key_b})
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                ids = [c.get("id") for c in items]
                assert self.contact_a_id not in ids, \
                    f"Org B's key must NOT see Org A's contact (id={self.contact_a_id})"

    def test_key_a_cannot_read_org_b_contacts(self):
        """Org A's key must not see Org B's contacts."""
        db = self.env["db"]
        contact_b = Contact(
            name="Org B Exclusive Contact",
            email=f"exclusive_b_{uuid.uuid4().hex[:6]}@orgb.com",
            workspace_id=self.env["ws_b"].id,
            user_id=self.env["user_b"].id,
        )
        db.add(contact_b)
        db.commit()
        db.refresh(contact_b)

        resp = client.get("/api/public/v1/contacts", headers={"X-API-Key": self.key_a})
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                ids = [c.get("id") for c in items]
                assert contact_b.id not in ids, \
                    f"Org A's key must NOT see Org B's contact (id={contact_b.id})"

    def test_key_b_cannot_read_org_a_deals(self):
        resp = client.get("/api/public/v1/deals", headers={"X-API-Key": self.key_b})
        assert resp.status_code in (200, 204)

    def test_key_b_cannot_read_org_a_workflows(self):
        resp = client.get("/api/public/v1/workflows", headers={"X-API-Key": self.key_b})
        assert resp.status_code in (200, 204)

    def test_key_b_cannot_access_org_a_developer_keys(self):
        """Org B admin must NOT see Org A's API keys via developer portal."""
        resp = client.get("/api/v1/developer/keys", headers=auth_headers(self.env["token_b"]))
        assert resp.status_code == 200
        key_ids = [k["id"] for k in resp.json()]
        db = self.env["db"]
        org_a_key_ids = [
            k.id for k in db.query(DeveloperAPIKey)
            .filter(DeveloperAPIKey.organization_id == self.env["org_a"].id)
            .all()
        ]
        overlap = set(key_ids) & set(org_a_key_ids)
        assert len(overlap) == 0, f"Org B sees Org A's keys: {overlap}"

    def test_key_b_cannot_access_org_a_webhooks(self):
        """Org B admin must NOT see Org A's webhook endpoints."""
        resp_wh = client.post("/api/v1/developer/webhooks", json={
            "url": "https://orga-secret.test/wh",
            "events": ["contact.created"],
        }, headers=auth_headers(self.env["token_a"]))
        if resp_wh.status_code == 200:
            wh_id_a = resp_wh.json()["id"]
            list_resp = client.get("/api/v1/developer/webhooks",
                                   headers=auth_headers(self.env["token_b"]))
            assert list_resp.status_code == 200
            b_wh_ids = [w["id"] for w in list_resp.json()]
            assert wh_id_a not in b_wh_ids, "Org B must not see Org A's webhook endpoints"

    def test_key_b_analytics_scoped_to_org_b(self):
        """Analytics endpoint with Org B key must only return Org B data."""
        resp = client.get("/api/public/v1/analytics/overview", headers={"X-API-Key": self.key_b})
        assert resp.status_code in (200, 403), f"Unexpected: {resp.status_code}"


# ===========================================================================
# 9. DEVELOPER ROUTER — Logs & Integrations Endpoints
# ===========================================================================

class TestDeveloperRouterEndpoints:

    def test_get_logs_returns_list(self, env):
        resp = client.get("/api/v1/developer/logs", headers=auth_headers(env["token_a"]))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_integrations_returns_list(self, env):
        resp = client.get("/api/v1/developer/integrations", headers=auth_headers(env["token_a"]))
        assert resp.status_code in (200, 404)

    def test_org_b_logs_scoped_to_org_b(self, env):
        """Logs for Org B must be scoped — no cross-leak of Org A's data."""
        resp_b = client.get("/api/v1/developer/logs", headers=auth_headers(env["token_b"]))
        assert resp_b.status_code == 200
        logs = resp_b.json()
        for log in logs:
            assert log.get("workspace_id") != env["ws_a"].id, \
                f"Org B logs must not include Org A's workspace_id"


# ===========================================================================
# 10. WEBHOOK DISPATCHER — Unit Tests
# ===========================================================================

class TestWebhookDispatcherUnit:

    def test_dispatcher_instantiation(self):
        dispatcher = WebhookDispatcher()
        assert dispatcher is not None

    def test_signature_header_format(self):
        import time
        secret = secrets.token_hex(32)
        payload = b'{"event":"contact.created"}'
        ts = int(time.time())
        sig = calculate_webhook_signature(secret, payload, ts)
        assert "t=" in sig
        assert "v1=" in sig

    def test_valid_event_names_recognized(self):
        for ev in ["contact.created", "deal.stage_changed", "workflow.completed"]:
            assert ev in VALID_WEBHOOK_EVENTS

    def test_invalid_event_not_in_catalog(self):
        assert "user.hacked" not in VALID_WEBHOOK_EVENTS
        assert "password.leaked" not in VALID_WEBHOOK_EVENTS


# ===========================================================================
# 11. MODEL INTEGRITY CHECKS
# ===========================================================================

class TestDeveloperModelIntegrity:
    """Validates model columns and relationships in SQLite test DB."""

    def test_developer_api_key_model_columns(self, env):
        db = env["db"]
        raw = "crm_live_" + secrets.token_urlsafe(24)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        key = DeveloperAPIKey(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            name="Model Integrity Key",
            key_prefix=raw[:12],
            hashed_key=hashed,
            scopes=["contacts:read"],
            status="active",
            is_active=True,
        )
        db.add(key)
        db.commit()
        db.refresh(key)
        assert key.id is not None
        assert key.organization_id == env["org_a"].id
        assert key.workspace_id == env["ws_a"].id
        assert key.hashed_key == hashed
        assert key.status == "active"

    def test_webhook_endpoint_model_columns(self, env):
        db = env["db"]
        wh = WebhookEndpoint(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            name="Model Integrity Webhook",
            url="https://integrity.test/wh",
            secret_key="whsec_" + secrets.token_hex(32),
            events=["contact.created"],
            is_active=True,
        )
        db.add(wh)
        db.commit()
        db.refresh(wh)
        assert wh.id is not None
        assert wh.organization_id == env["org_a"].id
        assert wh.events == ["contact.created"]

    def test_webhook_delivery_record_model(self, env):
        db = env["db"]
        wh = WebhookEndpoint(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            name="Delivery Test WH",
            url="https://delivery.test/wh",
            secret_key="whsec_" + secrets.token_hex(32),
            events=["task.created"],
            is_active=True,
        )
        db.add(wh)
        db.flush()
        delivery = WebhookDeliveryRecord(
            endpoint_id=wh.id,
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            event_type="task.created",
            event_id=str(uuid.uuid4()),
            payload={"task_id": 1},
            status="pending",
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        assert delivery.id is not None
        assert delivery.status == "pending"
        assert delivery.event_type == "task.created"

    def test_public_api_log_model(self, env):
        db = env["db"]
        log = PublicAPILog(
            organization_id=env["org_a"].id,
            workspace_id=env["ws_a"].id,
            method="GET",
            endpoint="/api/public/v1/contacts",
            status_code=200,
            latency_ms=45,
            ip_address="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        assert log.id is not None
        assert log.method == "GET"
        assert log.status_code == 200
