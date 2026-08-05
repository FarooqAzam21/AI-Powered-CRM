import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import get_auth_context, require_workspace_admin, AuthContext
from auth.models import Workspace, WorkspaceSetting, WorkspaceInvitation, Team, User

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspaces"])


# --- Schemas ---
class WorkspaceCreate(BaseModel):
    name: str
    type: Optional[str] = "Team" # Personal, Team, Enterprise
    brand_color: Optional[str] = "#6366f1"

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    brand_logo: Optional[str] = None
    brand_color: Optional[str] = None
    storage_quota_mb: Optional[int] = None
    ai_monthly_quota: Optional[int] = None

class WorkspaceSettingUpdate(BaseModel):
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    feature_flags: Optional[dict] = None

class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: Optional[str] = "Viewer"

class TeamCreate(BaseModel):
    name: str
    department_id: Optional[int] = None
    leader_id: Optional[int] = None


# --- Endpoints ---
@router.get("")
def list_my_workspaces(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """List all workspaces the current user has access to."""
    if not auth.user:
        raise HTTPException(401, "Not authenticated")
    workspaces = db.query(Workspace).filter(Workspace.users.any(id=auth.user.id)).all()
    return workspaces

@router.post("")
def create_workspace(data: WorkspaceCreate, auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """Create a new workspace and attach the creator as Workspace Admin."""
    if not auth.user:
        raise HTTPException(401, "Not authenticated")
    
    ws = Workspace(
        name=data.name,
        type=data.type or "Team",
        brand_color=data.brand_color or "#6366f1"
    )
    ws.users.append(auth.user)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # Initialize default settings
    settings = WorkspaceSetting(workspace_id=ws.id, feature_flags={
        "ai_copilot": True,
        "workflow_automation": True,
        "advanced_analytics": True
    })
    db.add(settings)
    db.commit()

    return ws

@router.get("/current")
def get_current_workspace(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """Get active workspace details and settings."""
    if not auth.workspace_id:
        raise HTTPException(400, "No active workspace context")
    ws = db.query(Workspace).filter(Workspace.id == auth.workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    
    settings = db.query(WorkspaceSetting).filter(WorkspaceSetting.workspace_id == ws.id).first()
    return {
        "workspace": ws,
        "settings": settings,
        "user_role": auth.role
    }

@router.patch("/current")
def update_current_workspace(
    data: WorkspaceUpdate,
    auth: AuthContext = Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    """Update workspace details & branding."""
    ws = db.query(Workspace).filter(Workspace.id == auth.workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")

    if data.name is not None: ws.name = data.name
    if data.brand_logo is not None: ws.brand_logo = data.brand_logo
    if data.brand_color is not None: ws.brand_color = data.brand_color
    if data.storage_quota_mb is not None: ws.storage_quota_mb = data.storage_quota_mb
    if data.ai_monthly_quota is not None: ws.ai_monthly_quota = data.ai_monthly_quota

    db.commit()
    db.refresh(ws)
    return ws

@router.patch("/current/settings")
def update_workspace_settings(
    data: WorkspaceSettingUpdate,
    auth: AuthContext = Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    """Update workspace AI config, email SMTP settings, and feature flags."""
    settings = db.query(WorkspaceSetting).filter(WorkspaceSetting.workspace_id == auth.workspace_id).first()
    if not settings:
        settings = WorkspaceSetting(workspace_id=auth.workspace_id)
        db.add(settings)

    if data.ai_provider is not None: settings.ai_provider = data.ai_provider
    if data.ai_model is not None: settings.ai_model = data.ai_model
    if data.smtp_host is not None: settings.smtp_host = data.smtp_host
    if data.smtp_port is not None: settings.smtp_port = data.smtp_port
    if data.feature_flags is not None: settings.feature_flags = data.feature_flags

    db.commit()
    db.refresh(settings)
    return settings

@router.post("/invite")
def invite_member(
    data: InviteMemberRequest,
    auth: AuthContext = Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    """Send an invitation to join the current workspace."""
    token = secrets.token_urlsafe(32)
    invitation = WorkspaceInvitation(
        workspace_id=auth.workspace_id,
        inviter_id=auth.user.id,
        email=data.email,
        role=data.role or "Viewer",
        token=token,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return {"message": f"Invitation created for {data.email}", "token": token, "invitation_id": invitation.id}

@router.get("/members")
def list_members(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """List members of the current workspace."""
    ws = db.query(Workspace).filter(Workspace.id == auth.workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws.users

@router.get("/teams")
def list_teams(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """List teams in the workspace."""
    return db.query(Team).filter(Team.workspace_id == auth.workspace_id).all()

@router.post("/teams")
def create_team(
    data: TeamCreate,
    auth: AuthContext = Depends(require_workspace_admin),
    db: Session = Depends(get_db)
):
    """Create a new team inside the workspace."""
    team = Team(
        workspace_id=auth.workspace_id,
        name=data.name,
        department_id=data.department_id,
        leader_id=data.leader_id
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
