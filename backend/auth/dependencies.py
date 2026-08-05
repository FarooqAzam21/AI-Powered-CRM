from fastapi import Depends, HTTPException, Request
from jose import jwt
from sqlalchemy.orm import Session
from database import get_db

from auth.rbac import (
    get_auth_context,
    AuthContext,
    require_super_admin,
    require_workspace_admin,
    require_security_analyst,
    require_viewer,
    Role
)

def get_current_user(auth: AuthContext = Depends(get_auth_context)):
    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found in auth context")
    return {
        "sub": auth.user.email,
        "role": auth.user.role,
        "workspace_id": auth.workspace_id,
        "organization_id": auth.organization_id,
        "user_id": auth.user.id,
    }

def get_current_user_model(auth: AuthContext = Depends(get_auth_context)):
    if not auth.user:
        raise HTTPException(status_code=401, detail="User not found")
    if auth.workspace_id is not None:
        auth.user.workspace_id = auth.workspace_id
    if auth.organization_id is not None:
        auth.user.organization_id = auth.organization_id
    return auth.user

# Mapping old dependencies to new RBAC
def require_user(auth: AuthContext = Depends(require_viewer)):
    return {"sub": auth.user.email, "role": auth.user.role}

def require_agent(auth: AuthContext = Depends(require_security_analyst)):
    return {"sub": auth.user.email, "role": auth.user.role}

def require_admin(auth: AuthContext = Depends(require_super_admin)):
    return {"sub": auth.user.email, "role": auth.user.role}
