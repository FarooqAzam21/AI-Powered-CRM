from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from auth.dependencies import require_super_admin, require_workspace_admin, AuthContext
from auth.models import Organization, Department, Team, User, UserGroup, WorkspacePolicy, AuditLog

router = APIRouter(prefix="/api/v1/organization", tags=["Organization Management"])


# --- Schemas ---
class OrgUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None

class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None

class UserUpdateOrg(BaseModel):
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    job_title: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class BulkInviteRequest(BaseModel):
    emails: List[EmailStr]
    role: Optional[str] = "Viewer"

class BulkRoleRequest(BaseModel):
    user_ids: List[int]
    role: str

class UserGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class PolicyCreate(BaseModel):
    name: str
    policy_type: str
    rules: dict


# --- Endpoints ---
@router.get("/profile")
def get_organization_profile(auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Get active organization profile details."""
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Default Enterprise", slug="default-org")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org

@router.patch("/profile")
def update_organization_profile(data: OrgUpdate, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Update organization settings."""
    org = db.query(Organization).first()
    if not org:
        raise HTTPException(404, "Organization not found")
    if data.name: org.name = data.name
    if data.domain: org.domain = data.domain
    if data.logo_url: org.logo_url = data.logo_url
    db.commit()
    db.refresh(org)
    return org

@router.get("/departments")
def list_departments(auth: AuthContext = Depends(get_db), db: Session = Depends(get_db)):
    """List departments in organization."""
    return db.query(Department).all()

@router.post("/departments")
def create_department(data: DepartmentCreate, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Create a new department."""
    org = db.query(Organization).first()
    dept = Department(organization_id=org.id if org else 1, name=data.name, code=data.code)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.get("/directory")
def get_employee_directory(auth: AuthContext = Depends(get_db), db: Session = Depends(get_db)):
    """Employee Directory with department and manager details."""
    users = db.query(User).all()
    directory = []
    for u in users:
        mgr = db.query(User).filter(User.id == u.manager_id).first() if u.manager_id else None
        dept = db.query(Department).filter(Department.id == u.department_id).first() if u.department_id else None
        directory.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "job_title": u.job_title,
            "status": u.status,
            "department": dept.name if dept else None,
            "manager": mgr.name if mgr else None
        })
    return directory

@router.patch("/users/{user_id}")
def update_user_org_info(user_id: int, data: UserUpdateOrg, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Manage job titles, department assignments, roles, manager relationships, and status."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(404, "User not found")
    
    if data.department_id is not None: target_user.department_id = data.department_id
    if data.manager_id is not None: target_user.manager_id = data.manager_id
    if data.job_title is not None: target_user.job_title = data.job_title
    if data.role is not None: target_user.role = data.role
    if data.status is not None: target_user.status = data.status

    db.commit()
    db.refresh(target_user)
    return target_user

@router.post("/users/bulk-invite")
def bulk_invite_users(data: BulkInviteRequest, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Bulk send invitations."""
    invited = []
    for email in data.emails:
        invited.append({"email": email, "role": data.role, "status": "queued"})
    return {"message": f"Bulk invitations processed for {len(data.emails)} users", "invited": invited}

@router.post("/users/bulk-role")
def bulk_assign_roles(data: BulkRoleRequest, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Bulk role reassignment."""
    db.query(User).filter(User.id.in_(data.user_ids)).update({User.role: data.role}, synchronize_session=False)
    db.commit()
    return {"message": f"Updated role to {data.role} for {len(data.user_ids)} users"}

@router.get("/user-groups")
def list_user_groups(auth: AuthContext = Depends(get_db), db: Session = Depends(get_db)):
    """List permission user groups."""
    return db.query(UserGroup).all()

@router.post("/user-groups")
def create_user_group(data: UserGroupCreate, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Create user group."""
    org = db.query(Organization).first()
    group = UserGroup(
        organization_id=org.id if org else 1,
        name=data.name,
        description=data.description,
        permissions=data.permissions
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

@router.get("/policies")
def list_workspace_policies(auth: AuthContext = Depends(get_db), db: Session = Depends(get_db)):
    """List enforced workspace policies."""
    return db.query(WorkspacePolicy).all()

@router.post("/policies")
def create_workspace_policy(data: PolicyCreate, auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db)):
    """Create a new workspace security or retention policy."""
    policy = WorkspacePolicy(
        workspace_id=auth.workspace_id or 1,
        name=data.name,
        policy_type=data.policy_type,
        rules=data.rules
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

@router.get("/audit-logs")
def get_organization_audit_logs(auth: AuthContext = Depends(require_super_admin), db: Session = Depends(get_db), limit: int = 100):
    """Retrieve organization activity audit log."""
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
