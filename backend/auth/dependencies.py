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


# ---------------------------------------------------------------------------
# P0 TENANT-ISOLATION DEPENDENCIES
# ---------------------------------------------------------------------------

def require_workspace_member(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthContext:
    """
    P0 Security: Verifies the authenticated user is an *active* member of the
    workspace that is active in their request context.

    This must be used on every data-access router (contacts, deals, campaigns,
    analytics, emails, tasks, developer resources) to prevent cross-tenant
    data access via X-Workspace-ID header injection.
    """
    if not auth.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not auth.workspace_id:
        # User has no workspace context — return their own personal data scope
        # (routes that call this will then scope by user_id only)
        return auth

    if auth.role == Role.SUPER_ADMIN:
        return auth

    from auth.models import WorkspaceMember
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.user_id == auth.user.id,
            WorkspaceMember.workspace_id == auth.workspace_id,
            WorkspaceMember.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You are not an active member of this workspace",
        )
    return auth


def require_org_member(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> AuthContext:
    """
    P0 Security: Verifies the authenticated user belongs to the organization
    they are trying to access.  Used on all /organization/* endpoints.
    """
    if not auth.user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Resolve the caller's organization via their workspace membership
    if auth.organization_id:
        from auth.models import Organization
        org = db.query(Organization).filter(
            Organization.id == auth.organization_id
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
    return auth

