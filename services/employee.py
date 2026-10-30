import math
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from database.models import Department, Employee
from services import department as department_service

SORT_FIELDS = {
    "name": Employee.name,
    "salary": Employee.salary,
    "joining_date": Employee.joining_date,
    "created_at": Employee.created_at,
}


def _db_error(db: Session):
    db.rollback()
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")


def get_or_404(db: Session, employee_id: int, with_department: bool = False) -> Employee:
    stmt = select(Employee).where(Employee.employee_id == employee_id)
    if with_department:
        stmt = stmt.options(joinedload(Employee.department))  # JOIN loads department too
    emp = db.scalars(stmt).first()
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Employee {employee_id} not found")
    return emp


def _require_department(db: Session, department_id: int):
    if not db.get(Department, department_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Department {department_id} not found")


def _email_taken(db: Session, email: str, exclude_id: Optional[int] = None) -> bool:
    stmt = select(Employee.employee_id).where(func.lower(Employee.email) == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(Employee.employee_id != exclude_id)
    return db.execute(stmt).first() is not None


def _commit(db: Session, obj):
    try:
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee email already exists or data violates a constraint")
    except SQLAlchemyError:
        _db_error(db)
    return obj


def create(db: Session, data) -> Employee:
    _require_department(db, data.department_id)
    if _email_taken(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee email already exists")
    emp = Employee(**data.model_dump())
    db.add(emp)
    return _commit(db, emp)


def list_employees(db: Session, *, page, limit, department_id=None, designation=None,
                   is_active=None, search=None, sort_by="created_at", sort_order="desc"):
    stmt = select(Employee)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if designation:
        stmt = stmt.where(Employee.designation.ilike(f"%{designation.strip()}%"))
    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Employee.name.ilike(like), Employee.email.ilike(like), Employee.designation.ilike(like)))

    try:
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        col = SORT_FIELDS[sort_by]
        stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc(), Employee.employee_id)
        items = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    except SQLAlchemyError:
        _db_error(db)
    return {"total": total, "page": page, "limit": limit,
            "total_pages": math.ceil(total / limit) if total else 0, "items": items}


def list_for_department(db: Session, department_id: int, **kwargs):
    department_service.get_or_404(db, department_id)
    return list_employees(db, department_id=department_id, **kwargs)


def update(db: Session, employee_id: int, data, partial: bool = False) -> Employee:
    emp = get_or_404(db, employee_id)
    values = data.model_dump(exclude_unset=True) if partial else data.model_dump()
    if partial and not values:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")
    for required in ("name", "email", "age", "designation", "salary", "department_id", "joining_date", "is_active"):
        if required in values and values[required] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{required} cannot be null")

    if "department_id" in values and values["department_id"] != emp.department_id:
        _require_department(db, values["department_id"])
    if "email" in values and _email_taken(db, values["email"], exclude_id=employee_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee email already exists")
    for k, v in values.items():
        setattr(emp, k, v)
    return _commit(db, emp)


def delete(db: Session, employee_id: int) -> Employee:
    """Soft delete (is_active = false)."""
    emp = get_or_404(db, employee_id)
    emp.is_active = False
    return _commit(db, emp)


def statistics(db: Session) -> dict:
    try:
        row = db.execute(
            select(
                func.count(Employee.employee_id),
                func.coalesce(func.sum(case((Employee.is_active.is_(True), 1), else_=0)), 0),
                func.coalesce(func.avg(Employee.salary), 0),
                func.coalesce(func.max(Employee.salary), 0),
                func.coalesce(func.min(Employee.salary), 0),
            )
        ).one()
    except SQLAlchemyError:
        _db_error(db)
    total, active = int(row[0]), int(row[1])
    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": total - active,
        "average_salary": round(float(row[2]), 2),
        "highest_salary": float(row[3]),
        "lowest_salary": float(row[4]),
    }
