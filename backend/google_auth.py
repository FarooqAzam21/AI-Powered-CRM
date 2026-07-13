from datetime import timedelta
from urllib.parse import urlencode
import uuid
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth.auth_manager import create_user, get_db
from auth.jwt import create_access_token, get_password_hash
from auth.models import User
from config.settings import get_settings
from utils.security import encrypt_secret

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/google", tags=["Google Integration"])
settings = get_settings()


def _oauth_configured() -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_client_secret not in {"", "your_client_secret_here"}
    )


def _build_auth_url(intent: str = "login") -> str:
    scope = (
        "openid email profile "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send"
    )
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": f"{intent}:{uuid.uuid4()}",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _issue_app_token(user: User, gmail_connected: bool = True) -> str:
    return create_access_token(
        {
            "sub": user.email,
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "gmail_connected": gmail_connected,
        },
        timedelta(days=7),
    )


def _redirect_frontend(path: str) -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    return RedirectResponse(f"{base}{path}", status_code=303)


@router.get("/config")
def google_config():
    return {
        "enabled": _oauth_configured() or not settings.google_client_secret,
        "simulation_mode": not _oauth_configured(),
        "redirect_uri": settings.google_redirect_uri,
    }


@router.get("/login")
def google_login(intent: str = Query("login", pattern="^(login|signup)$")):
    """Start Google OAuth — creates account on first sign-in (signup) or links Gmail on login."""
    if not settings.google_client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID is not configured in .env")

    if not _oauth_configured():
        return {"url": f"{settings.google_redirect_uri}?code=simulated_code&state={intent}:sim"}

    return {"url": _build_auth_url(intent)}


@router.get("/signup")
def google_signup():
    """Alias for Google registration — same OAuth flow, auto-creates user if new."""
    return google_login(intent="signup")


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        intent = state.split(":", 1)[0] if state else "login"
        logger.info("Google callback intent=%s", intent)

        if not _oauth_configured() or code == "simulated_code":
            sim_email = "testuser@gmail.com"
            user = db.query(User).filter(User.email == sim_email).first()
            if not user:
                user = create_user(
                    {
                        "name": "Test User",
                        "email": sim_email,
                        "password": get_password_hash(uuid.uuid4().hex),
                        "role": "user",
                        "is_verified": True,
                        "gmail_connected": True,
                    }
                )
            else:
                user.gmail_connected = True
                db.commit()
                db.refresh(user)

            token = _issue_app_token(user)
            return _redirect_frontend(f"/auth/callback?token={token}&provider=google&intent={intent}")

        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
            timeout=20,
        )
        if token_res.status_code != 200:
            logger.error("Google token error: %s", token_res.text)
            return _redirect_frontend("/login?error=token_failed")

        tokens = token_res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        profile_res = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        if profile_res.status_code != 200:
            return _redirect_frontend("/login?error=profile_failed")

        profile = profile_res.json()
        email = profile.get("email")
        name = profile.get("name") or email.split("@")[0]

        if not email:
            return _redirect_frontend("/login?error=no_email")

        user = db.query(User).filter(User.email == email).first()
        is_new = user is None

        if is_new:
            user = create_user(
                {
                    "name": name,
                    "email": email,
                    "password": get_password_hash(uuid.uuid4().hex),
                    "role": "user",
                    "is_verified": True,
                    "gmail_connected": True,
                    "google_access_token": encrypt_secret(access_token),
                    "google_refresh_token": encrypt_secret(refresh_token or ""),
                }
            )
        else:
            user.name = user.name or name
            user.google_access_token = encrypt_secret(access_token)
            if refresh_token:
                user.google_refresh_token = encrypt_secret(refresh_token)
            user.gmail_connected = True
            user.is_verified = True
            db.commit()
            db.refresh(user)

        app_token = _issue_app_token(user)
        redirect_intent = "signup" if is_new and intent == "signup" else "login"
        return _redirect_frontend(
            f"/auth/callback?token={app_token}&provider=google&intent={redirect_intent}&new={'1' if is_new else '0'}"
        )
    except Exception as exc:
        logger.exception("Google callback failed: %s", exc)
        return _redirect_frontend("/login?error=internal_error")
