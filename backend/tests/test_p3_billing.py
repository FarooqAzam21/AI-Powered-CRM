import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import User, Workspace, Organization, WorkspaceMember
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role
from billing.models import Plan, Subscription, SubscriptionHistory, UsageCounter, BillingWebhookEvent
from billing.plans import seed_default_plans, PLAN_DEFAULTS
from billing.service import BillingService
from billing.providers.mock_provider import MockPaymentProvider
from billing.webhooks import BillingWebhookHandler

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_billing_p3.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def create_token(email: str, role: str, org_id: int, ws_id: int):
    payload = {
        "sub": email,
        "role": role,
        "organization_id": org_id,
        "workspace_id": ws_id,
        "exp": datetime.utcnow() + timedelta(hours=2),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture(scope="module")
def setup_billing_test():
    import uuid
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed default billing plans
    seed_default_plans(db)

    # Create test organizations with unique slugs
    uid = uuid.uuid4().hex[:6]
    org1 = Organization(name="Billing Org 1", slug=f"billing-org-1-{uid}")
    org2 = Organization(name="Billing Org 2", slug=f"billing-org-2-{uid}")
    db.add(org1)
    db.add(org2)
    db.commit()
    db.refresh(org1)
    db.refresh(org2)

    # Create test workspaces
    ws1 = Workspace(name="Workspace 1", organization_id=org1.id)
    ws2 = Workspace(name="Workspace 2", organization_id=org2.id)
    db.add(ws1)
    db.add(ws2)
    db.commit()
    db.refresh(ws1)
    db.refresh(ws2)

    # Create admin and viewer users
    admin1 = User(
        name="Admin One",
        email="admin1@billingtest.com",
        password="hashed_pw",
        role=Role.WORKSPACE_ADMIN,
        workspace_id=ws1.id,
        organization_id=org1.id,
        is_verified=True,
    )
    viewer1 = User(
        name="Viewer One",
        email="viewer1@billingtest.com",
        password="hashed_pw",
        role=Role.VIEWER,
        workspace_id=ws1.id,
        organization_id=org1.id,
        is_verified=True,
    )
    db.add(admin1)
    db.add(viewer1)
    db.commit()
    db.refresh(admin1)
    db.refresh(viewer1)

    # Workspace memberships
    m1 = WorkspaceMember(workspace_id=ws1.id, organization_id=org1.id, user_id=admin1.id, role=Role.WORKSPACE_ADMIN, status="active")
    m2 = WorkspaceMember(workspace_id=ws1.id, organization_id=org1.id, user_id=viewer1.id, role=Role.VIEWER, status="active")
    db.add(m1)
    db.add(m2)
    db.commit()

    token_admin = create_token(admin1.email, admin1.role, org1.id, ws1.id)
    token_viewer = create_token(viewer1.email, viewer1.role, org1.id, ws1.id)

    yield {
        "db": db,
        "org1": org1,
        "org2": org2,
        "admin1": admin1,
        "viewer1": viewer1,
        "token_admin": token_admin,
        "token_viewer": token_viewer,
    }

    db.close()


def test_list_plans(setup_billing_test):
    response = client.get("/api/v1/billing/plans")
    assert response.status_code == 200
    plans = response.json()
    slugs = [p["slug"] for p in plans]
    assert "free" in slugs
    assert "starter" in slugs
    assert "professional" in slugs
    assert "enterprise" in slugs


def test_subscription_auto_initialization(setup_billing_test):
    context = setup_billing_test
    token = context["token_admin"]
    response = client.get(
        "/api/v1/billing/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "subscription" in data
    assert "plan" in data
    assert data["subscription"]["organization_id"] == context["org1"].id
    assert data["subscription"]["status"] in ("active", "trial")


def test_quota_checking_and_increment(setup_billing_test):
    context = setup_billing_test
    db = context["db"]
    org_id = context["org1"].id

    # Initially 0 contacts
    res = BillingService.check_quota(org_id, "contacts", 1, db)
    assert res.allowed is True

    # Free plan has 100 contacts limit. Set usage to 99
    BillingService.set_usage(org_id, "contacts", 99, db)
    res = BillingService.check_quota(org_id, "contacts", 1, db)
    assert res.allowed is True
    assert res.remaining == 1

    # Requesting 2 contacts exceeds limit 100
    res_exceeded = BillingService.check_quota(org_id, "contacts", 2, db)
    assert res_exceeded.allowed is False

    # Increment usage by 1 -> now 100
    count = BillingService.increment_usage(org_id, "contacts", 1, db)
    assert count == 100

    # Next 1 contact is denied
    res_full = BillingService.check_quota(org_id, "contacts", 1, db)
    assert res_full.allowed is False


def test_feature_flags(setup_billing_test):
    context = setup_billing_test
    db = context["db"]
    org_id = context["org1"].id

    # Free plan has basic_crm, but not advanced_analytics
    assert BillingService.has_feature(org_id, "basic_crm", db) is True
    assert BillingService.has_feature(org_id, "advanced_analytics", db) is False


def test_upgrade_plan_and_feature_unlock(setup_billing_test):
    context = setup_billing_test
    token = context["token_admin"]
    db = context["db"]
    org_id = context["org1"].id

    # Upgrade to Professional
    response = client.post(
        "/api/v1/billing/subscribe",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_slug": "professional", "interval": "month"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify features now unlocked
    assert BillingService.has_feature(org_id, "advanced_analytics", db) is True
    assert BillingService.has_feature(org_id, "workflow_automation", db) is True

    # Check contact quota on Professional (10,000 limit)
    res = BillingService.check_quota(org_id, "contacts", 1, db)
    assert res.allowed is True
    assert res.limit == 10000


def test_rbac_viewer_cannot_manage_billing(setup_billing_test):
    context = setup_billing_test
    viewer_token = context["token_viewer"]

    # Viewer cannot change subscription
    response = client.post(
        "/api/v1/billing/subscribe",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"plan_slug": "enterprise", "interval": "month"},
    )
    assert response.status_code == 403

    # Viewer cannot cancel subscription
    cancel_resp = client.post(
        "/api/v1/billing/cancel",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert cancel_resp.status_code == 403


def test_cancel_subscription(setup_billing_test):
    context = setup_billing_test
    admin_token = context["token_admin"]

    response = client.post(
        "/api/v1/billing/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Check subscription status is canceled
    sub_resp = client.get(
        "/api/v1/billing/subscription",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sub_resp.json()["subscription"]["status"] == "canceled"


def test_webhook_idempotency_and_processing(setup_billing_test):
    context = setup_billing_test
    db = context["db"]

    # Prepare webhook event
    event_id = "evt_test_unique_123"
    payload = {
        "id": event_id,
        "type": "invoice.payment_succeeded",
        "data": {
            "id": "sub_mock_xyz",
            "customer_id": "mock_cus_default",
        },
    }

    # First call: processed
    resp1 = client.post(
        "/api/v1/billing/webhooks/mock",
        headers={"x-webhook-signature": "test_valid_sig"},
        json=payload,
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "processed"

    # Second call with same event_id: idempotent ignored
    resp2 = client.post(
        "/api/v1/billing/webhooks/mock",
        headers={"x-webhook-signature": "test_valid_sig"},
        json=payload,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_processed"


def test_mock_payment_provider():
    provider = MockPaymentProvider()
    cust_id = provider.create_customer(org_id=99, email="test@mock.org", name="Mock Org")
    assert cust_id.startswith("mock_cus_")

    checkout = provider.create_checkout(customer_id=cust_id, plan_slug="starter")
    assert checkout.session_id.startswith("cs_test_")
    assert "checkout-success" in checkout.checkout_url

    sub = provider.get_subscription("sub_test_123")
    assert sub.status == "active"
