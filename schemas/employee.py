from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schemas.department import DepartmentBrief


def _non_empty(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("must not be empty")
    return v


class EmployeeBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    age: int = Field(..., ge=18, le=70, description="Must be between 18 and 70")
    designation: str = Field(..., max_length=100)
    salary: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    department_id: int = Field(..., gt=0)
    is_active: bool = True
    joining_date: date = Field(default_factory=date.today)

    _v = field_validator("name", "designation")(_non_empty)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    """PUT - full update."""


class EmployeePatch(BaseModel):
    """PATCH - partial update."""
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    age: Optional[int] = Field(None, ge=18, le=70)
    designation: Optional[str] = Field(None, max_length=100)
    salary: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    department_id: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    joining_date: Optional[date] = None

    _v = field_validator("name", "designation")(_non_empty)


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    created_at: datetime
    updated_at: datetime


class EmployeeDetail(EmployeeResponse):
    """Employee with nested department information."""
    department: DepartmentBrief


class EmployeeList(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[EmployeeResponse]


class EmployeeStatistics(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    average_salary: float
    highest_salary: float
    lowest_salary: float
