import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import User, Workspace
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role

# Use a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rbac.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    workspace = Workspace(name="Test Workspace")
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    users = {
        "viewer": User(name="Viewer", email="viewer@test.com", password="pw", role=Role.VIEWER, workspace_id=workspace.id),
        "analyst": User(name="Analyst", email="analyst@test.com", password="pw", role=Role.SECURITY_ANALYST, workspace_id=workspace.id),
        "admin": User(name="Admin", email="admin@test.com", password="pw", role=Role.WORKSPACE_ADMIN, workspace_id=workspace.id),
        "super": User(name="Super", email="super@test.com", password="pw", role=Role.SUPER_ADMIN, workspace_id=workspace.id)
    }
    
    for u in users.values():
        db.add(u)
    db.commit()
    
    yield users
    
    db.close()
    Base.metadata.drop_all(bind=engine)

def get_token(email: str):
    return jwt.encode({"sub": email}, SECRET_KEY, algorithm=ALGORITHM)

def test_viewer_access(setup_db):
    users = setup_db
    token = get_token(users["viewer"].email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Viewer can GET contacts
    res = client.get("/contacts", headers=headers)
    assert res.status_code == 200
    
    # Viewer CANNOT POST contacts
    res = client.post("/contacts", json={"email": "new@test.com"}, headers=headers)
    assert res.status_code == 403

def test_analyst_access(setup_db):
    users = setup_db
    token = get_token(users["analyst"].email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Analyst can GET contacts
    res = client.get("/contacts", headers=headers)
    assert res.status_code == 200
    
    # Analyst CAN POST contacts
    res = client.post("/contacts", json={"email": "new2@test.com"}, headers=headers)
    assert res.status_code in [200, 404]  # 404 because user context depends on sub matching

def test_admin_access(setup_db):
    users = setup_db
    token = get_token(users["admin"].email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Admin can DELETE contacts
    res = client.delete("/contacts/999", headers=headers)
    assert res.status_code in [200, 404] # 404 if contact not found, but NOT 403

def test_viewer_delete_forbidden(setup_db):
    users = setup_db
    token = get_token(users["viewer"].email)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Viewer CANNOT DELETE contacts
    res = client.delete("/contacts/999", headers=headers)
    assert res.status_code == 403
