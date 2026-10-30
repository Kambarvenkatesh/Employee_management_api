from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from dependencies.auth import require_role
from dependencies.user_query import user_list_params
from schemas.user import UserList
from services import user as service

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_role("admin"))])


@router.get("/users", response_model=UserList)
def admin_list_users(params: dict = Depends(user_list_params), db: Session = Depends(get_db)):
    """All users - **admin only**. Pagination, search, role / active filters, sorting."""
    return service.list_users(db, **params)
