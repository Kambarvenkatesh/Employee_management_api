from typing import Literal, Optional

from fastapi import Query

from database.models import UserRole
from schemas.user import UserSortField


def user_list_params(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter active / inactive users"),
    sort_by: UserSortField = "user_id",
    sort_order: Literal["asc", "desc"] = "asc",
) -> dict:
    """Shared pagination / search / filter / sort params for every 'list users' endpoint."""
    return dict(page=page, limit=limit, search=search, role=role, is_active=is_active,
                sort_by=sort_by, sort_order=sort_order)
