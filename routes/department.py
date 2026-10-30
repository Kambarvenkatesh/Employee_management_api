from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from dependencies.auth import get_current_user, require_role
from schemas.department import (DepartmentCreate, DepartmentList, DepartmentPatch,
                                DepartmentResponse, DepartmentSummary, DepartmentUpdate)
from schemas.employee import EmployeeList
from services import department as service
from services import employee as employee_service

# Every department endpoint needs a valid token. Listing/viewing departments is open to any
# logged-in user; anything that exposes employees or salaries, and all writes, need admin/manager;
# delete is admin only.
router = APIRouter(prefix="/departments", tags=["Departments"], dependencies=[Depends(get_current_user)])
staff_only = [Depends(require_role("admin", "manager"))]
admin_only = [Depends(require_role("admin"))]
DeptId = Path(..., gt=0, description="Department ID (positive integer)")


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED,
             dependencies=staff_only)
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    return service.create(db, data)


@router.get("", response_model=DepartmentList)
def list_departments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort_by: Literal["department_name", "created_at", "department_id"] = "department_id",
    sort_order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
):
    return service.list_departments(db, page=page, limit=limit, search=search, is_active=is_active, sort_by=sort_by, sort_order=sort_order)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(department_id: int = DeptId, db: Session = Depends(get_db)):
    return service.get_or_404(db, department_id)


@router.put("/{department_id}", response_model=DepartmentResponse, dependencies=staff_only)
def replace_department(data: DepartmentUpdate, department_id: int = DeptId, db: Session = Depends(get_db)):
    return service.update(db, department_id, data)


@router.patch("/{department_id}", response_model=DepartmentResponse, dependencies=staff_only)
def patch_department(data: DepartmentPatch, department_id: int = DeptId, db: Session = Depends(get_db)):
    return service.update(db, department_id, data, partial=True)


@router.delete("/{department_id}", response_model=DepartmentResponse, dependencies=admin_only)
def delete_department(department_id: int = DeptId, db: Session = Depends(get_db)):
    """Soft delete: sets is_active = false."""
    return service.soft_delete(db, department_id)


@router.get("/{department_id}/employees", response_model=EmployeeList, dependencies=staff_only)
def department_employees(
    department_id: int = DeptId,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort_by: Literal["name", "salary", "joining_date", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    return employee_service.list_for_department(
        db, department_id, page=page, limit=limit, search=search,
        is_active=is_active, sort_by=sort_by, sort_order=sort_order)


@router.get("/{department_id}/summary", response_model=DepartmentSummary, dependencies=staff_only)
def department_summary(department_id: int = DeptId, db: Session = Depends(get_db)):
    return service.summary(db, department_id)
