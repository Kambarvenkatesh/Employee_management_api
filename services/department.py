import math
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database.models import Department, Employee

SORT_FIELDS = {
    "department_name": Department.department_name,
    "created_at": Department.created_at,
    "department_id": Department.department_id,
}


def get_or_404(db: Session, department_id: int) -> Department:
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Department {department_id} not found")
    return dept


def _name_taken(db: Session, name: str, exclude_id: Optional[int] = None) -> bool:
    stmt = select(Department.department_id).where(func.lower(Department.department_name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Department.department_id != exclude_id)
    return db.execute(stmt).first() is not None


def _commit(db: Session, obj):
    try:
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Department name already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")
    return obj


def create(db: Session, data) -> Department:
    if _name_taken(db, data.department_name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Department name already exists")
    dept = Department(**data.model_dump())
    db.add(dept)
    return _commit(db, dept)


def list_departments(db: Session, *, page, limit, search, is_active, sort_by, sort_order):
    stmt = select(Department)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Department.department_name.ilike(like), Department.description.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    col = SORT_FIELDS[sort_by]
    stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc(), Department.department_id)
    items = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    return {"total": total, "page": page, "limit": limit,
            "total_pages": math.ceil(total / limit) if total else 0, "items": items}


def update(db: Session, department_id: int, data, partial: bool = False) -> Department:
    dept = get_or_404(db, department_id)
    values = data.model_dump(exclude_unset=True) if partial else data.model_dump()
    if partial and not values:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")
    new_name = values.get("department_name")
    if new_name and _name_taken(db, new_name, exclude_id=department_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Department name already exists")
    for k, v in values.items():
        if k in ("department_name", "is_active") and v is None:
            continue
        setattr(dept, k, v)
    return _commit(db, dept)


def soft_delete(db: Session, department_id: int) -> Department:
    dept = get_or_404(db, department_id)
    dept.is_active = False
    return _commit(db, dept)


def summary(db: Session, department_id: int) -> dict:
    dept = get_or_404(db, department_id)
    try:
        row = db.execute(
            select(
                func.count(Employee.employee_id),
                func.coalesce(func.sum(case((Employee.is_active.is_(True), 1), else_=0)), 0),
                func.coalesce(func.avg(Employee.salary), 0),
            ).where(Employee.department_id == department_id)
        ).one()
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")
    total, active, avg = int(row[0]), int(row[1]), float(row[2])
    return {
        "department_id": dept.department_id,
        "department_name": dept.department_name,
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": total - active,
        "average_salary": round(avg, 2),
    }
