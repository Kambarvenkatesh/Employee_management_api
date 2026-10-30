import math
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import User, UserRole
from utils.password import hash_password

SORT_FIELDS = {
    "user_id": User.user_id,
    "name": User.name,
    "email": User.email,
    "role": User.role,
    "created_at": User.created_at,
}


def _db_error(db: Session):
    db.rollback()
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalars(select(User).where(func.lower(User.email) == email.strip().lower())).first()


def get_or_404(db: Session, user_id: int) -> User:
    user = get_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found")
    return user


def _commit(db: Session, user: User) -> User:
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    except SQLAlchemyError:
        _db_error(db)
    return user


def create_user(db: Session, *, name: str, email: str, password: str,
                role: UserRole = UserRole.user, is_active: bool = True) -> User:
    """Create a user. Only the bcrypt hash of `password` is ever stored."""
    if get_by_email(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(name=name, email=email.strip().lower(), password_hash=hash_password(password),
                role=role, is_active=is_active)
    db.add(user)
    return _commit(db, user)


def list_users(db: Session, *, page: int, limit: int, search: Optional[str] = None,
               role: Optional[UserRole] = None, is_active: Optional[bool] = None,
               sort_by: str = "user_id", sort_order: str = "asc") -> dict:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like)))
    try:
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        col = SORT_FIELDS[sort_by]
        stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc(), User.user_id)
        items = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    except SQLAlchemyError:
        _db_error(db)
    return {"total": total, "page": page, "limit": limit,
            "total_pages": math.ceil(total / limit) if total else 0, "items": items}


def update(db: Session, user_id: int, data, actor: User) -> User:
    """PUT / PATCH. The caller's access to this user_id is checked by a route dependency;
    here we enforce the field-level rules (only admins may change role / is_active)."""
    user = get_or_404(db, user_id)
    values = data.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")
    for field, value in values.items():
        if value is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{field} cannot be null")

    is_admin = actor.role == UserRole.admin
    role_changes = "role" in values and values["role"] != user.role
    active_changes = "is_active" in values and values["is_active"] != user.is_active
    if (role_changes or active_changes) and not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can change role or active status")
    if actor.user_id == user.user_id and is_admin:
        if role_changes or (active_changes and values["is_active"] is False):
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "Admins cannot demote or deactivate their own account")

    if "email" in values:
        other = get_by_email(db, values["email"])
        if other and other.user_id != user.user_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    for field, value in values.items():
        setattr(user, field, value)
    return _commit(db, user)


def deactivate(db: Session, user_id: int, actor: User) -> User:
    """Soft delete: sets is_active = false (the row is kept)."""
    user = get_or_404(db, user_id)
    if actor.user_id == user.user_id and actor.role == UserRole.admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot deactivate their own account")
    user.is_active = False
    return _commit(db, user)
