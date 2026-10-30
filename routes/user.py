from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from dependencies.auth import get_current_user, require_role, require_self_or_role
from dependencies.user_query import user_list_params
from schemas.user import UserList, UserPatch, UserResponse, UserUpdate
from services import user as service

router = APIRouter(prefix="/users", tags=["Users"])
UserId = Path(..., gt=0, description="User ID (positive integer)")


@router.get("", response_model=UserList, dependencies=[Depends(require_role("admin", "manager"))])
def list_users(params: dict = Depends(user_list_params), db: Session = Depends(get_db)):
    """admin / manager only."""
    return service.list_users(db, **params)


@router.get("/{user_id}", response_model=UserResponse,
            dependencies=[Depends(require_self_or_role("admin", "manager"))])
def get_user(user_id: int = UserId, db: Session = Depends(get_db)):
    """Your own record, or any record if you are admin / manager."""
    return service.get_or_404(db, user_id)


@router.put("/{user_id}", response_model=UserResponse,
            dependencies=[Depends(require_self_or_role("admin"))])
def replace_user(data: UserUpdate, user_id: int = UserId, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    """Full update. Admin: any user. Others: only themselves, and not role / is_active."""
    return service.update(db, user_id, data, current_user)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_self_or_role("admin"))])
def patch_user(data: UserPatch, user_id: int = UserId, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    """Partial update. Same rules as PUT."""
    return service.update(db, user_id, data, current_user)


@router.delete("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_self_or_role("admin"))])
def deactivate_user(user_id: int = UserId, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    """Soft delete: sets is_active = false. Admin: any user. Others: only themselves."""
    return service.deactivate(db, user_id, current_user)
