from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os
import requests
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

from auth.auth_manager import get_db, create_user
from auth.models import User
from auth.jwt import create_access_token

router = APIRouter(prefix="/google", tags=["Google Integration"])

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Redirect to Backend directly
REDIRECT_URI = "http://localhost:8000/google/callback" 

@router.get("/login")
def login(db: Session = Depends(get_db)):
    """
    Generates the Google OAuth URL. 
    If in simulation mode, redirects directly to the callback.
    """
    # 1. Simulation Mode Check
    if not CLIENT_SECRET or CLIENT_SECRET == "your_client_secret_here":
        print("DEBUG: Simulation Login Detected. Bypassing Google...")
        # Redirect to our own callback with a mock code
        return {"url": f"http://localhost:8000/google/callback?code=simulated_code&state=sim_state"}

    if not CLIENT_ID:
        raise HTTPException(500, "Google Client ID not configured")
        
    # Added 'profile' and 'email' scopes to get user info
    scope = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send openid email profile"
    
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(uuid.uuid4()) 
    }
    
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"url": url}

@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        print(f"DEBUG: Callback received. Code: {code[:10]}...")

        # 1. Simulation Mode (If secret is missing)
        if not CLIENT_SECRET or CLIENT_SECRET == "your_client_secret_here":
            print("DEBUG: Simulation Mode Active.")
            sim_email = "testuser@gmail.com"
            sim_user = db.query(User).filter(User.email == sim_email).first()
            
            if not sim_user:
                print(f"DEBUG: Creating simulated user {sim_email}")
                sim_user = create_user({
                    "name": "Test User",
                    "email": sim_email,
                    "password": "simulated_password",
                    "role": "user",
                    "is_verified": True,
                    "gmail_connected": True
                })
            else:
                # Ensure connected state
                sim_user.gmail_connected = True
                db.commit()

            # Generate Token for this valid user
            token = create_access_token(
                {"sub": sim_user.email, "name": sim_user.name, "role": sim_user.role, "gmail_connected": True}, 
                timedelta(days=1)
            )
            return RedirectResponse(f"http://localhost:5173/auth/callback?token={token}", status_code=303)

        # 2. Exchange Code for Tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI
        }
        
        print("DEBUG: Exchanging token with Google...")
        res = requests.post(token_url, data=data)
        if res.status_code != 200:
            print(f"DEBUG: Google Token Error: {res.text}")
            return RedirectResponse("http://localhost:5173/login?error=token_failed", status_code=303)
            
        tokens = res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        id_token = tokens.get("id_token") # JWT from Google containing profile

        # 3. Get User Profile
        profile_res = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        if profile_res.status_code != 200:
             print("DEBUG: Failed to fetch user profile")
             return RedirectResponse("http://localhost:5173/login?error=profile_failed", status_code=303)
        
        profile = profile_res.json()
        email = profile.get("email")
        name = profile.get("name", "Google User")
        
        print(f"DEBUG: Authenticated Google User: {email}")

        # 4. DB Upsert
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print("DEBUG: Creating new user from Google Login")
            user = create_user({
                "name": name,
                "email": email,
                "password": "google_oauth_user", 
                "role": "user",
                "is_verified": True, 
                "gmail_connected": True,
                "google_access_token": access_token,
                "google_refresh_token": refresh_token
            })
        else:
            print("DEBUG: Updating existing user tokens")
            user.google_access_token = access_token
            if refresh_token:
                user.google_refresh_token = refresh_token
            user.gmail_connected = True
            db.commit()

        # 5. Generate App Session Token
        app_token = create_access_token(
            {"sub": user.email, "name": user.name, "role": user.role, "gmail_connected": True},
            timedelta(days=7)
        )
        
        # 6. Redirect to Frontend Callback
        return RedirectResponse(f"http://localhost:5173/auth/callback?token={app_token}", status_code=303)

    except Exception as e:
        print(f"CRITICAL ERROR in /google/callback: {str(e)}")
        return RedirectResponse("http://localhost:5173/login?error=internal_error", status_code=303)
