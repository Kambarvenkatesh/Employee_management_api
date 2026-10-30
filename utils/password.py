"""Password hashing (bcrypt) and password-strength rules."""
import re

import bcrypt

from utils.config import settings

MIN_LENGTH = 8
MAX_BYTES = 72  # bcrypt only uses the first 72 bytes; we reject longer input instead of truncating silently
_SPECIALS = r"""!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~"""


def validate_password_strength(password: str) -> str:
    """Raise ValueError describing every unmet rule; return the password if valid."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_BYTES:
        problems.append(f"at most {MAX_BYTES} bytes")
    if not re.search(r"[A-Z]", password):
        problems.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        problems.append("one lowercase letter")
    if not re.search(r"\d", password):
        problems.append("one number")
    if not re.search(f"[{_SPECIALS}]", password):
        problems.append("one special character")
    if problems:
        raise ValueError("Password must contain " + ", ".join(problems))
    return password


def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash (the salt is embedded in the result)."""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time check of a plain password against a stored hash."""
    raw = plain_password.encode("utf-8")
    if len(raw) > MAX_BYTES:  # can never match a hash we created
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:  # malformed hash
        return False
