from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import User, UserRole
from services import user as user_service
from utils.config import settings
from utils.jwt import create_access_token
from utils.password import hash_password, verify_password

# Verified against when the email is unknown, so "no such email" and "wrong password"
# take the same time and can't be told apart by timing.
_DUMMY_HASH = hash_password("dummy-password-for-timing")

INVALID_CREDENTIALS = "Invalid email or password"


def register(db: Session, data, actor: Optional[User]) -> User:
    """Public registration. Anyone may register as `user`; manager/admin needs an admin caller."""
    if data.role != UserRole.user and not settings.ALLOW_OPEN_ROLE_REGISTRATION:
        if actor is None or actor.role != UserRole.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Only an admin can create manager or admin accounts")
    return user_service.create_user(
        db, name=data.name, email=data.email, password=data.password, role=data.role)


def login(db: Session, data) -> dict:
    user = user_service.get_by_email(db, data.email)
    password_ok = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok:
        # Same status + message for both cases: never reveal which one was wrong.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS,
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def change_password(db: Session, user: User, data) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "New password must be different from the current password")
    user.password_hash = hash_password(data.new_password)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")
