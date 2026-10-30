from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_user, get_optional_user
from schemas.auth import (ChangePasswordRequest, LoginRequest, MessageResponse,
                          RegisterRequest, TokenResponse)
from schemas.user import UserResponse
from services import auth as service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db),
             actor: Optional[User] = Depends(get_optional_user)):
    """Create an account. Open to everyone for `role: user`.
    Creating a `manager` or `admin` requires an **admin** token (use Authorize first)."""
    return service.register(db, data, actor)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Exchange email + password for a JWT access token."""
    return service.login(db, data)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """The currently logged-in user."""
    return current_user


@router.patch("/change-password", response_model=MessageResponse)
def change_password(data: ChangePasswordRequest, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    service.change_password(db, current_user, data)
    return {"message": "Password updated successfully"}
