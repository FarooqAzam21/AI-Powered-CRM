from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from auth.jwt import ALGORITHM, SECRET_KEY
from auth.models import User
from database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_model(
    token: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.email == token["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_user(token: dict = Depends(get_current_user)):
    return token


def require_agent(token: dict = Depends(get_current_user)):
    if token["role"] != "agent":
        raise HTTPException(status_code=403)
    return token


def require_admin(token: dict = Depends(get_current_user)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403)
    return token
