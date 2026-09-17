from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime
import uuid
from sqlalchemy.orm import Session

from auth.jwt import create_access_token, get_password_hash, verify_password, create_refresh_token, hash_refresh_token
from auth.auth_manager import find_user_by_email, create_user
from database import get_db
from auth.dependencies import get_current_user
from typing import Optional
import re
from auth.models import User, RefreshToken, Organization, Workspace, WorkspaceMember, WorkspaceSetting
from auth.rbac import Role
from config.settings import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Auth"])

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"
    workspace_name: Optional[str] = None

class Login(BaseModel):
    email: str
    password: str

def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    )

@router.post("/register")
def register(data: Register, response: Response, db: Session = Depends(get_db)):
    print(f"DEBUG: Registration attempt for {data.email}")
    if find_user_by_email(data.email, db=db):
        print(f"DEBUG: Registration failed - user {data.email} already exists")
        raise HTTPException(400, "User exists")

    clean_name = data.name.strip()
    org_slug = re.sub(r'[^a-zA-Z0-9-]', '-', clean_name.lower()).strip('-') or "org"
    org_slug = f"{org_slug}-{uuid.uuid4().hex[:6]}"
    org = Organization(name=f"{clean_name}'s Organization", slug=org_slug)
    db.add(org)
    db.commit()
    db.refresh(org)

    ws_name = data.workspace_name.strip() if (data.workspace_name and data.workspace_name.strip()) else f"{clean_name}'s Workspace"
    ws = Workspace(
        name=ws_name,
        organization_id=org.id,
        type="Team",
        brand_color="#6366f1"
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    ws_setting = WorkspaceSetting(
        workspace_id=ws.id,
        feature_flags={
            "ai_copilot": True,
            "workflow_automation": True,
            "advanced_analytics": True
        }
    )
    db.add(ws_setting)

    user_role = data.role if data.role != "user" else Role.WORKSPACE_ADMIN
    user = create_user({
        "name": data.name,
        "email": data.email,
        "password": get_password_hash(data.password),
        "role": user_role,
        "verification_token": None,
        "is_verified": True,
        "workspace_id": ws.id,
        "organization_id": org.id,
    }, db=db)

    ws.users.append(user)

    member = WorkspaceMember(
        workspace_id=ws.id,
        organization_id=org.id,
        user_id=user.id,
        role=Role.WORKSPACE_ADMIN,
        status="active"
    )
    db.add(member)
    db.commit()
    db.refresh(user)

    print(f"DEBUG: User {data.email} created with workspace {ws.name} ({ws.id}).")

    # Auto-login after registration
    token_payload = {
        "sub": user.email,
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "gmail_connected": getattr(user, 'gmail_connected', False),
        "workspace_id": user.workspace_id,
        "organization_id": user.organization_id,
    }
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    db.add(db_refresh)
    db.commit()

    set_refresh_cookie(response, refresh_token)

    return {
        "message": "Registration successful!",
        "access_token": token,
        "refresh_token": refresh_token,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "workspace_id": user.workspace_id,
        "organization_id": user.organization_id,
        "gmail_connected": getattr(user, 'gmail_connected', False)
    }

@router.post("/login")
def login(data: Login, response: Response, db: Session = Depends(get_db)):
    print(f"DEBUG: Login attempt for {data.email}")
    user = find_user_by_email(data.email, db=db)

    if not user:
        print(f"DEBUG: Login failed - user {data.email} not found")
        raise HTTPException(401, "Invalid credentials")
        
    if not verify_password(data.password, user.password):
        print(f"DEBUG: Login failed - incorrect password for {data.email}")
        raise HTTPException(401, "Invalid credentials")
    
    if not user.is_verified:
        print(f"DEBUG: Login failed - user {data.email} not verified")
        raise HTTPException(403, "Email not verified. Please check your inbox.")

    print(f"DEBUG: Login successful for {data.email}")

    if user.workspace_id is None:
        first_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active"
        ).first()
        if first_member:
            user.workspace_id = first_member.workspace_id
            user.organization_id = first_member.organization_id
            db.commit()
            db.refresh(user)

    token_payload = {
        "sub": user.email,
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "gmail_connected": getattr(user, 'gmail_connected', False),
        "workspace_id": user.workspace_id,
        "organization_id": user.organization_id,
    }
    
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    db.add(db_refresh)
    db.commit()

    set_refresh_cookie(response, refresh_token)

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "workspace_id": user.workspace_id,
        "organization_id": user.organization_id,
        "gmail_connected": getattr(user, 'gmail_connected', False)
    }

@router.get("/me")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "gmail_connected": getattr(user, 'gmail_connected', False),
    }

@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(400, "Invalid or expired token")
    
    if user.is_verified:
        return {"message": "Email already verified!"}
        
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully! You can now login."}

class RefreshRequest(BaseModel):
    refresh_token: str = None

@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
    data: RefreshRequest = None,
    db: Session = Depends(get_db)
):
    token = None
    if data and data.refresh_token:
        token = data.refresh_token
    elif request.cookies.get("refresh_token"):
        token = request.cookies.get("refresh_token")
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(401, "Refresh token missing")

    token_hash = hash_refresh_token(token)
    db_refresh = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not db_refresh:
        raise HTTPException(401, "Invalid refresh token")

    if db_refresh.revoked_at or db_refresh.replaced_by:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == db_refresh.user_id,
            RefreshToken.revoked_at == None
        ).update({"revoked_at": datetime.utcnow()})
        db.commit()
        response.delete_cookie("refresh_token")
        raise HTTPException(400, "Token has already been used or revoked. All active sessions terminated.")

    if db_refresh.expires_at < datetime.utcnow():
        raise HTTPException(401, "Refresh token expired")

    user = db.query(User).filter(User.id == db_refresh.user_id).first()
    if not user:
        raise HTTPException(401, "User not found")

    token_payload = {
        "sub": user.email,
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "gmail_connected": getattr(user, 'gmail_connected', False),
        "workspace_id": user.workspace_id,
        "organization_id": user.organization_id,
    }
    
    new_access_token = create_access_token(token_payload)
    new_refresh_token = create_refresh_token(token_payload)
    new_hash = hash_refresh_token(new_refresh_token)

    new_db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    db.add(new_db_refresh)

    db_refresh.revoked_at = datetime.utcnow()
    db_refresh.replaced_by = new_hash
    db.commit()

    set_refresh_cookie(response, new_refresh_token)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    data: RefreshRequest = None,
    db: Session = Depends(get_db)
):
    token = None
    if data and data.refresh_token:
        token = data.refresh_token
    elif request.cookies.get("refresh_token"):
        token = request.cookies.get("refresh_token")
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if token:
        token_hash = hash_refresh_token(token)
        db_refresh = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if db_refresh and not db_refresh.revoked_at:
            db_refresh.revoked_at = datetime.utcnow()
            db.commit()

    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.post("/revoke-all")
def revoke_all(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.get("id") or current_user.get("user_id")
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at == None
    ).update({"revoked_at": datetime.utcnow()})
    db.commit()
    return {"message": "All sessions revoked successfully"}
