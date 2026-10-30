from pydantic import BaseModel, EmailStr, Field, field_validator

from database.models import UserRole
from schemas.user import clean_name, normalize_email
from utils.password import validate_password_strength


class RegisterRequest(BaseModel):
    name: str = Field(..., max_length=100, examples=["Rahul"])
    email: EmailStr = Field(..., examples=["rahul@example.com"])
    password: str = Field(..., examples=["Password@123"])
    role: UserRole = Field(UserRole.user, description="admin / manager / user. Only admins may create admin/manager accounts.")

    _v_name = field_validator("name")(clean_name)
    _v_email = field_validator("email", mode="before")(normalize_email)
    _v_password = field_validator("password")(validate_password_strength)


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["rahul@example.com"])
    # No strength rules on login: we only compare against the stored hash.
    password: str = Field(..., min_length=1, max_length=128, examples=["Password@123"])

    _v_email = field_validator("email", mode="before")(normalize_email)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Seconds until the token expires")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str

    _v_new = field_validator("new_password")(validate_password_strength)


class MessageResponse(BaseModel):
    message: str
