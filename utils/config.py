"""Central place for security-related settings (read from environment / .env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # bcrypt work factor. 12 is a good default; tests lower it for speed.
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # If false (default), only an authenticated admin may create manager/admin
    # accounts through POST /auth/register. Anyone can still register as "user".
    # Set to true ONLY for demos where you want to pick any role on register.
    ALLOW_OPEN_ROLE_REGISTRATION: bool = _get_bool("ALLOW_OPEN_ROLE_REGISTRATION", False)


settings = Settings()

if not settings.JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Add it to your .env file or environment, e.g.\n"
        '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
