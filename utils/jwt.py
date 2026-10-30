"""JWT creation / decoding. Nothing here touches the database or FastAPI."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt  # PyJWT (absolute import -> the library, not this module)

from utils.config import settings


class TokenExpiredError(Exception):
    """The token's `exp` claim is in the past."""


class TokenInvalidError(Exception):
    """Bad signature, malformed token, wrong algorithm or missing claims."""


def create_access_token(user, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user.user_id),          # user ID (JWT spec requires `sub` to be a string)
        "email": user.email,
        "role": getattr(user.role, "value", user.role),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],   # pinned: blocks "alg: none" tricks
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise TokenInvalidError()
