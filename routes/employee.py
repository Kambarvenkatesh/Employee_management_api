from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from dependencies.auth import get_current_user, require_role
from schemas.employee import (EmployeeCreate, EmployeeDetail, EmployeeList, EmployeePatch,
                              EmployeeResponse, EmployeeStatistics, EmployeeUpdate)
from services import employee as service

# Every employee endpoint needs a valid token. Employee records include salary, so reads are
# limited to admin/manager; writes to admin/manager; delete to admin only.
router = APIRouter(prefix="/employees", tags=["Employees"], dependencies=[Depends(get_current_user)])
staff_only = [Depends(require_role("admin", "manager"))]
admin_only = [Depends(require_role("admin"))]
EmpId = Path(..., gt=0, description="Employee ID (positive integer)")


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED,
             dependencies=staff_only)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    return service.create(db, data)


@router.get("", response_model=EmployeeList, dependencies=staff_only)
def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    department_id: Optional[int] = Query(None, gt=0),
    designation: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Search by name, email or designation"),
    sort_by: Literal["name", "salary", "joining_date", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    return service.list_employees(
        db, page=page, limit=limit, department_id=department_id, designation=designation,
        is_active=is_active, search=search, sort_by=sort_by, sort_order=sort_order)


# NOTE: must be declared before "/{employee_id}" so "statistics" isn't parsed as an ID.
@router.get("/statistics", response_model=EmployeeStatistics, dependencies=staff_only)
def employee_statistics(db: Session = Depends(get_db)):
    return service.statistics(db)


@router.get("/{employee_id}", response_model=EmployeeDetail, dependencies=staff_only)
def get_employee(employee_id: int = EmpId, db: Session = Depends(get_db)):
    return service.get_or_404(db, employee_id, with_department=True)


@router.put("/{employee_id}", response_model=EmployeeResponse, dependencies=staff_only)
def replace_employee(data: EmployeeUpdate, employee_id: int = EmpId, db: Session = Depends(get_db)):
    return service.update(db, employee_id, data)


@router.patch("/{employee_id}", response_model=EmployeeResponse, dependencies=staff_only)
def patch_employee(data: EmployeePatch, employee_id: int = EmpId, db: Session = Depends(get_db)):
    return service.update(db, employee_id, data, partial=True)


@router.delete("/{employee_id}", response_model=EmployeeResponse, dependencies=admin_only)
def delete_employee(employee_id: int = EmpId, db: Session = Depends(get_db)):
    """Soft delete: sets is_active = false."""
    return service.delete(db, employee_id)
