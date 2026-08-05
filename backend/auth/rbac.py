from enum import Enum
import hashlib
import secrets
from fastapi import Depends, HTTPException, Security, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_
from jose import jwt
from datetime import datetime

from database import get_db
from auth.jwt import ALGORITHM, SECRET_KEY
from auth.models import User, APIKey, AuditLog
from utils.rate_limiter import check_rate_limits

class Role(str, Enum):
    SUPER_ADMIN = "Super Admin"
    WORKSPACE_ADMIN = "Workspace Admin"
    SECURITY_ANALYST = "Security Analyst"
    VIEWER = "Viewer"

ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: 40,
    Role.WORKSPACE_ADMIN: 30,
    Role.SECURITY_ANALYST: 20,
    Role.VIEWER: 10
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def log_audit(db: Session, action: str, resource: str, status: str, user_id: int = None, workspace_id: int = None, details: str = None, request: Request = None):
    ip_address = request.client.host if request and request.client else None
    audit = AuditLog(
        action=action,
        resource=resource,
        status=status,
        user_id=user_id,
        workspace_id=workspace_id,
        details=details,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()

class AuthContext:
    def __init__(self, user: User = None, api_key: APIKey = None, active_workspace_id: int = None, active_organization_id: int = None):
        self.user = user
        self.api_key = api_key
        self.workspace_id = active_workspace_id or (user.workspace_id if user else (api_key.workspace_id if api_key else None))
        self.organization_id = active_organization_id or getattr(user, "organization_id", None)
        if user:
            self.role = user.role
        elif api_key:
            self.role = Role.WORKSPACE_ADMIN 
        else:
            self.role = None

def validate_api_key_scopes(scopes: list, method: str, path: str) -> bool:
    if not scopes:
        return False
    if "admin" in scopes or "*" in scopes:
        return True
    path = path.lower().rstrip("/")
    method = method.upper()
    if "/contacts" in path:
        return "contacts.read" in scopes or "crm.read" in scopes if method in ["GET", "OPTIONS"] else "contacts.write" in scopes or "crm.write" in scopes
    if "/emails" in path or "/inbox" in path:
        return "emails.read" in scopes or "crm.read" in scopes if method in ["GET", "OPTIONS"] else "emails.write" in scopes or "crm.write" in scopes
    if "/campaigns" in path:
        return "campaigns.read" in scopes or "crm.read" in scopes if method in ["GET", "OPTIONS"] else "campaigns.write" in scopes or "crm.write" in scopes
    if "/analytics" in path:
        return "analytics.read" in scopes or "crm.read" in scopes
    if "/pipelines" in path or "/deals" in path or "/crm" in path:
        return "crm.read" in scopes if method in ["GET", "OPTIONS"] else "crm.write" in scopes
    if "/ai" in path:
        if "reply" in path: return "ai.reply" in scopes
        if "classify" in path: return "ai.classify" in scopes
        if "score" in path: return "ai.score" in scopes
        return "ai.reply" in scopes or "ai.classify" in scopes or "ai.score" in scopes
    if "/users" in path:
        return "users.read" in scopes
    if "/settings" in path:
        return "settings.read" in scopes
    return True

def get_auth_context(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
    api_key_str: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> AuthContext:
    
    # Optional workspace switching header
    requested_workspace_id = request.headers.get("X-Workspace-ID")
    requested_org_id = request.headers.get("X-Organization-ID")
    active_ws_id = int(requested_workspace_id) if requested_workspace_id and requested_workspace_id.isdigit() else None
    active_org_id = int(requested_org_id) if requested_org_id and requested_org_id.isdigit() else None

    # Check if request has an API Key either in X-API-Key or Authorization Bearer header
    actual_api_key = api_key_str or (token if token and token.startswith("crm_") else None)
    
    if actual_api_key:
        hashed = hashlib.sha256(actual_api_key.encode('utf-8')).hexdigest()
        prefix = actual_api_key[:12] if actual_api_key.startswith("crm_") else None
        
        query = db.query(APIKey).filter(APIKey.status == "active")
        if prefix:
            query = query.filter(or_(APIKey.key_prefix == prefix, APIKey.key == actual_api_key))
        else:
            query = query.filter(APIKey.key == actual_api_key)
            
        keys = query.all()
        matched_key = None
        for k in keys:
            if k.hashed_key:
                if secrets.compare_digest(k.hashed_key, hashed):
                    matched_key = k
                    break
            elif k.key == actual_api_key:
                matched_key = k
                break
                
        if not matched_key:
            log_audit(db, "API_KEY_AUTH", request.url.path, "DENIED", details="Invalid or inactive API Key", request=request)
            raise HTTPException(status_code=401, detail="Invalid API Key")
            
        # Check expiration
        if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
            matched_key.status = "expired"
            db.commit()
            log_audit(db, "API_KEY_AUTH", request.url.path, "DENIED", details="Expired API Key", request=request)
            raise HTTPException(status_code=401, detail="API Key has expired")
            
        # Enforce scope checks
        scopes = matched_key.permissions or []
        if not validate_api_key_scopes(scopes, request.method, request.url.path):
            log_audit(db, "API_KEY_AUTH", request.url.path, "DENIED", details=f"Insufficient scopes. Got: {scopes}", request=request)
            raise HTTPException(status_code=403, detail="Insufficient API key scopes")
            
        # Enforce rate limiting
        allowed, remaining, retry_after = check_rate_limits(
            matched_key.id, 
            matched_key.rate_limit or 60, 
            matched_key.daily_limit or 1000
        )
        
        # Expose rate limit headers
        response.headers["X-RateLimit-Limit"] = str(matched_key.rate_limit or 60)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(retry_after if retry_after > 0 else 60 - (int(datetime.utcnow().timestamp()) % 60))
        
        if not allowed:
            response.headers["Retry-After"] = str(retry_after)
            log_audit(db, "API_KEY_AUTH", request.url.path, "DENIED", details="Rate limit exceeded", request=request)
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(matched_key.rate_limit or 60),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after)
                }
            )
            
        # Update last used details
        matched_key.last_used_at = datetime.utcnow()
        matched_key.last_ip = request.client.host if request.client else None
        db.commit()
        
        # Save key details in request.state for auditing middleware
        request.state.api_key_id = matched_key.id
        request.state.workspace_id = matched_key.workspace_id
        
        # Map context user to API Key owner user profile for backend compatibility
        owner = db.query(User).filter(User.id == matched_key.owner_id).first() if matched_key.owner_id else None
        return AuthContext(user=owner, api_key=matched_key, active_workspace_id=matched_key.workspace_id, active_organization_id=active_org_id)

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user = db.query(User).filter(User.email == payload.get("sub")).first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return AuthContext(user=user, active_workspace_id=active_ws_id or user.workspace_id, active_organization_id=active_org_id or getattr(user, "organization_id", None))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    raise HTTPException(status_code=401, detail="Not authenticated")

def require_role(min_role: Role):
    def role_checker(request: Request, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
        user_role_level = ROLE_HIERARCHY.get(auth.role, 0)
        min_role_level = ROLE_HIERARCHY.get(min_role, 0)

        if user_role_level < min_role_level:
            user_id = auth.user.id if auth.user else None
            log_audit(db, "ACCESS", request.url.path, "DENIED", user_id=user_id, workspace_id=auth.workspace_id, details=f"Requires {min_role}, got {auth.role}", request=request)
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return auth
    return role_checker

# Pre-defined dependencies
require_super_admin = require_role(Role.SUPER_ADMIN)
require_workspace_admin = require_role(Role.WORKSPACE_ADMIN)
require_security_analyst = require_role(Role.SECURITY_ANALYST)
require_viewer = require_role(Role.VIEWER)
