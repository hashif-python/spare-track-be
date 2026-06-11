from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import decode_token
from app.auth.service import get_user_by_id
from app.common.exceptions import ForbiddenException, UnauthorizedException
from app.database import get_db


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    payload = decode_token(token)

    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    token_type = payload.get("type")

    if token_type != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    user = get_user_by_id(db, int(user_id))

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise ForbiddenException("User account is inactive")

    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise ForbiddenException("Admin permission required")

    return current_user