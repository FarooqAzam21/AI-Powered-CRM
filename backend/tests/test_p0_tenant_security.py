import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import User, Workspace, Organization, WorkspaceMember, Department
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role
from auth.ws_auth import verify_ws_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_tenant_security.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create Organizations
    org_a = Organization(name="Org A", slug="org-a")
    org_b = Organization(name="Org B", slug="org-b")
    db.add(org_a)
    db.add(org_b)
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)

    # Create Workspaces
    ws_a = Workspace(name="Workspace A", organization_id=org_a.id)
    ws_b = Workspace(name="Workspace B", organization_id=org_b.id)
    db.add(ws_a)
    db.add(ws_b)
    db.commit()
    db.refresh(ws_a)
    db.refresh(ws_b)

    # Create Users
    user_a = User(
        name="User A",
        email="a@test.com",
        password="pw",
        role=Role.VIEWER,
        workspace_id=ws_a.id,
        organization_id=org_a.id,
        is_verified=True
    )
    user_b = User(
        name="User B",
        email="b@test.com",
        password="pw",
        role=Role.VIEWER,
        workspace_id=ws_b.id,
        organization_id=org_b.id,
        is_verified=True
    )
    db.add(user_a)
    db.add(user_b)
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    # Create Active Workspace Memberships
    member_a = WorkspaceMember(
        workspace_id=ws_a.id,
        organization_id=org_a.id,
        user_id=user_a.id,
        role=Role.VIEWER,
        status="active"
    )
    member_b = WorkspaceMember(
        workspace_id=ws_b.id,
        organization_id=org_b.id,
        user_id=user_b.id,
        role=Role.VIEWER,
        status="active"
    )
    db.add(member_a)
    db.add(member_b)
    db.commit()

    # Create Departments
    dept_a = Department(organization_id=org_a.id, name="Dept A")
    dept_b = Department(organization_id=org_b.id, name="Dept B")
    db.add(dept_a)
    db.add(dept_b)
    db.commit()

    yield {
        "org_a": org_a,
        "org_b": org_b,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "user_a": user_a,
        "user_b": user_b,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def get_token(email: str, workspace_id: int = None, organization_id: int = None):
    payload = {"sub": email}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if organization_id:
        payload["organization_id"] = organization_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_valid_member_retains_access(setup_db):
    data = setup_db
    token = get_token(data["user_a"].email, data["ws_a"].id, data["org_a"].id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(data["ws_a"].id)
    }
    res = client.get("/contacts", headers=headers)
    assert res.status_code == 200


def test_user_a_cannot_access_workspace_b(setup_db):
    data = setup_db
    token = get_token(data["user_a"].email, data["ws_b"].id, data["org_b"].id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(data["ws_b"].id)
    }
    # User A tries to access Workspace B
    res = client.get("/contacts", headers=headers)
    assert res.status_code == 403
    assert "not an active member of this workspace" in res.json()["detail"]


def test_workspace_id_header_injection_cannot_bypass_membership(setup_db):
    data = setup_db
    # Token claims workspace_a, but header claims workspace_b
    token = get_token(data["user_a"].email, data["ws_a"].id, data["org_a"].id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(data["ws_b"].id)
    }
    res = client.get("/contacts", headers=headers)
    assert res.status_code == 403


def test_unauthenticated_organization_endpoints_return_401(setup_db):
    res = client.get("/api/v1/organization/departments")
    assert res.status_code == 401


def test_org_directory_is_authenticated_and_scoped(setup_db):
    data = setup_db
    token = get_token(data["user_a"].email, data["ws_a"].id, data["org_a"].id)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(data["ws_a"].id),
        "X-Organization-ID": str(data["org_a"].id)
    }
    res = client.get("/api/v1/organization/directory", headers=headers)
    assert res.status_code == 200
    directory = res.json()
    # Directory should only return User A (Org A), not User B (Org B)
    emails = [user["email"] for user in directory]
    assert "a@test.com" in emails
    assert "b@test.com" not in emails


def test_websocket_unauthorized_returns_none(setup_db):
    data = setup_db
    db = TestingSessionLocal()
    try:
        # Invalid token
        user = verify_ws_user(db, data["user_a"].id, "invalid-token")
        assert user is None

        # User A tries to connect as User B
        token_a = get_token(data["user_a"].email, data["ws_a"].id, data["org_a"].id)
        user = verify_ws_user(db, data["user_b"].id, token_a)
        assert user is None

        # Active workspace validation failure (User A tries to claim Workspace B)
        token_spoof = get_token(data["user_a"].email, data["ws_b"].id, data["org_b"].id)
        user = verify_ws_user(db, data["user_a"].id, token_spoof)
        assert user is None
    finally:
        db.close()
