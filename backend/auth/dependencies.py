from fastapi import Depends, HTTPException
from jose import jwt
from auth.jwt import SECRET_KEY, ALGORITHM

def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_user(token: str = Depends(get_current_user)):
    return token

def require_agent(token: str = Depends(get_current_user)):
    if token["role"] != "agent":
        raise HTTPException(status_code=403)
    return token

def require_admin(token: str = Depends(get_current_user)):
    if token["role"] != "admin":
        raise HTTPException(status_code=403)
    return token
