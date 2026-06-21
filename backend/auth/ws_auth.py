from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth.jwt import ALGORITHM, SECRET_KEY
from auth.models import User


def verify_ws_user(db: Session, user_id: int, token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.id == user_id, User.email == email).first()
        return user
    except JWTError:
        return None
