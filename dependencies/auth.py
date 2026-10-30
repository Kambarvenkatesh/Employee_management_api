
from typing import Optional

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, UserRole
from services import user as user_service
from utils.jwt import TokenExpiredError, TokenInvalidError, decode_access_token

# Makes Swagger show the "Authorize" button (paste the JWT from POST /auth/login).
# auto_error=False so *we* decide the status code/message (always 401, never 403).
bearer_scheme = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description="Paste the `access_token` returned by **POST /auth/login** (no 'Bearer ' prefix needed).",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise _unauthorized("Token has expired")
    except TokenInvalidError:
        raise _unauthorized("Invalid token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _unauthorized("Invalid token")

    # Always re-load the user: role changes and deactivation take effect immediately,
    # we never trust the role claim inside the token for authorization.
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise _unauthorized("Invalid token")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated")
    return _user_from_token(credentials.credentials, db)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """For endpoints open to everyone that behave differently for logged-in users.
    No token -> None. A token that IS supplied must still be valid."""
    if credentials is None or not credentials.credentials:
        return None
    return _user_from_token(credentials.credentials, db)


def require_role(*roles):
    """Dependency factory: `Depends(require_role("admin", "manager"))`."""
    allowed = {UserRole(r) for r in roles}  # raises at import time on a typo'd role

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "You do not have permission to perform this action")
        return current_user

    return checker


def require_self_or_role(*roles):
    """Allow the user whose id is in the path (`/users/{user_id}`), or any of `roles`.
    Checked before the lookup, so non-privileged callers get 403 whether or not the
    target exists (no user-enumeration)."""
    allowed = {UserRole(r) for r in roles}

    def checker(
        user_id: int = Path(..., gt=0, description="User ID (positive integer)"),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.user_id != user_id and current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "You do not have permission to access this user")
        return current_user

    return checker
