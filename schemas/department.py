from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_name(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("department_name cannot be empty")
    return v


class DepartmentBase(BaseModel):
    department_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True

    _v_name = field_validator("department_name")(_clean_name)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(DepartmentBase):
    """PUT - full update."""


class DepartmentPatch(BaseModel):
    """PATCH - partial update."""
    department_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    _v_name = field_validator("department_name")(_clean_name)


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    department_id: int
    created_at: datetime
    updated_at: datetime


class DepartmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department_id: int
    department_name: str


class DepartmentList(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[DepartmentResponse]


class DepartmentSummary(BaseModel):
    department_id: int
    department_name: str
    total_employees: int
    active_employees: int
    inactive_employees: int
    average_salary: float
