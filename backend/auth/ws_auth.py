from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth.jwt import ALGORITHM, SECRET_KEY
from auth.models import User, WorkspaceMember
from auth.rbac import Role


def verify_ws_user(db: Session, user_id: int, token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.id == user_id, User.email == email).first()
        if not user:
            return None

        # Verify workspace membership
        workspace_id = payload.get("workspace_id") or user.workspace_id
        if workspace_id and user.role != Role.SUPER_ADMIN:
            membership = db.query(WorkspaceMember).filter(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "active"
            ).first()
            if not membership:
                return None

        return user
    except JWTError:
        return None
