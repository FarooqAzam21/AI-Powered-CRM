import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from datetime import timedelta
from unittest import mock

from main import app
from database import Base, get_db
from auth.models import User, RefreshToken
from auth.auth_manager import get_db as auth_get_db

# Test Database setup — StaticPool forces all connections to reuse the same
# in-memory SQLite connection so tables created in setup are visible to the
# FastAPI test client running in a worker thread.
from sqlalchemy.pool import StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
    # Mock passlib to bypass bcrypt 4.0+ 72-byte self-test bug
    with mock.patch("auth.jwt.verify_password", return_value=True), \
         mock.patch("auth.auth_router.verify_password", return_value=True):
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[auth_get_db] = override_get_db
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        
        # Create test user
        user = User(
            name="Refresh Test User",
            email="refresh@test.com",
            password="hashed_password",
            role="user",
            is_verified=True
        )
        user.gmail_connected = False
        db.add(user)
        db.commit()
        db.refresh(user)

        yield {"db": db, "user": user}

    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def test_login_returns_refresh_token(setup_db):
    res = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Check if cookie is set
    assert "refresh_token" in client.cookies

def test_refresh_token_rotation(setup_db):
    # 1. Login to get initial tokens
    res = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    initial_refresh = res.json()["refresh_token"]
    
    # 2. Refresh using the token
    res2 = client.post("/auth/refresh", json={"refresh_token": initial_refresh})
    assert res2.status_code == 200
    data2 = res2.json()
    assert "access_token" in data2
    assert "refresh_token" in data2
    new_refresh = data2["refresh_token"]
    
    # They should be different (rotation)
    assert initial_refresh != new_refresh

def test_refresh_token_reuse_detection(setup_db):
    # 1. Login to get initial tokens
    res = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    initial_refresh = res.json()["refresh_token"]
    
    # 2. Refresh using the token (it gets rotated and old becomes invalid)
    client.post("/auth/refresh", json={"refresh_token": initial_refresh})
    
    # 3. Try to use the OLD token again (replay attack)
    res_reuse = client.post("/auth/refresh", json={"refresh_token": initial_refresh})
    assert res_reuse.status_code == 400
    assert "already been used or revoked" in res_reuse.json()["detail"]

def test_logout_revokes_token(setup_db):
    # 1. Login
    res = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    refresh_token = res.json()["refresh_token"]
    
    # 2. Logout
    res_logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert res_logout.status_code == 200
    
    # 3. Try to refresh with the logged-out token
    res_refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res_refresh.status_code == 400  # Reuse/revoked detection kicks in

def test_revoke_all_sessions(setup_db):
    # 1. Login on device A
    res_a = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    token_a = res_a.json()["refresh_token"]
    access_a = res_a.json()["access_token"]
    
    # 2. Login on device B
    res_b = client.post("/auth/login", json={"email": "refresh@test.com", "password": "password123"})
    token_b = res_b.json()["refresh_token"]
    
    # 3. Revoke all using device A's access token
    res_revoke = client.post("/auth/revoke-all", headers={"Authorization": f"Bearer {access_a}"})
    assert res_revoke.status_code == 200
    
    # 4. Try to refresh device A
    res_refresh_a = client.post("/auth/refresh", json={"refresh_token": token_a})
    assert res_refresh_a.status_code == 400
    
    # 5. Try to refresh device B
    res_refresh_b = client.post("/auth/refresh", json={"refresh_token": token_b})
    assert res_refresh_b.status_code == 400
