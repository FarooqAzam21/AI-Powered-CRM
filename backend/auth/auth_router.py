from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import timedelta
import uuid
from sqlalchemy.orm import Session

from auth.jwt import create_access_token, get_password_hash, verify_password
from auth.auth_manager import find_user_by_email, create_user, get_db
from auth.dependencies import get_current_user
from auth.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"

class Login(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(data: Register, db: Session = Depends(get_db)):
    print(f"DEBUG: Registration attempt for {data.email}")
    if find_user_by_email(data.email):
        print(f"DEBUG: Registration failed - user {data.email} already exists")
        raise HTTPException(400, "User exists")

    user = create_user({
        "name": data.name,
        "email": data.email,
        "password": get_password_hash(data.password),
        "role": data.role,
        "verification_token": None,
        "is_verified": True
    })
    
    print(f"DEBUG: User {data.email} created successfully.")

    # Auto-login after registration
    token = create_access_token(
        {"sub": user.email, "id": user.id, "name": user.name, "role": user.role, "gmail_connected": user.gmail_connected},
        timedelta(days=1)
    )

    return {
        "message": "Registration successful!",
        "access_token": token,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "gmail_connected": user.gmail_connected
    }

@router.post("/login")
def login(data: Login):
    print(f"DEBUG: Login attempt for {data.email}")
    user = find_user_by_email(data.email)

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

    token = create_access_token(
        {"sub": user.email, "id": user.id, "name": user.name, "role": user.role, "gmail_connected": user.gmail_connected},
        timedelta(days=1)
    )

    return {
        "access_token": token,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "gmail_connected": user.gmail_connected
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
        "gmail_connected": user.gmail_connected,
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
