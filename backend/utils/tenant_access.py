from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from auth.models import WorkspaceSetting, Workspace


def workspace_feature_enabled(db: Session, workspace_id: int | None, feature: str, default: bool = True) -> bool:
    if not workspace_id:
        return default
    settings = db.query(WorkspaceSetting).filter(WorkspaceSetting.workspace_id == workspace_id).first()
    flags = settings.feature_flags or {} if settings else {}
    return bool(flags.get(feature, default))


def workspace_quota_exceeded(db: Session, workspace_id: int | None, used: int, limit_key: str = "storage_quota_mb") -> bool:
    if not workspace_id:
        return False
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return False
    limit = getattr(workspace, limit_key, None)
    if limit is None:
        return False
    return used >= limit
