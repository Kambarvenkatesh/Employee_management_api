from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from database.models import UserRole


def clean_name(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = " ".join(v.split())  # trim + collapse inner whitespace
    if len(v) < 2:
        raise ValueError("name must be at least 2 characters")
    return v


def normalize_email(v):
    return v.strip().lower() if isinstance(v, str) else v


class UserResponse(BaseModel):
    """Public view of a user. There is deliberately no password / password_hash field."""
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """PUT - full update of profile fields. `role` / `is_active` are admin-only and optional."""
    name: str = Field(..., max_length=100)
    email: EmailStr
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    _v_name = field_validator("name")(clean_name)
    _v_email = field_validator("email", mode="before")(normalize_email)


class UserPatch(BaseModel):
    """PATCH - partial update."""
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    _v_name = field_validator("name")(clean_name)
    _v_email = field_validator("email", mode="before")(normalize_email)


class UserList(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[UserResponse]


UserSortField = Literal["user_id", "name", "email", "role", "created_at"]
