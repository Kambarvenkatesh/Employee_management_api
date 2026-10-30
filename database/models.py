import enum

from sqlalchemy import (Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer,
                        Numeric, String, Text, func)
from sqlalchemy.orm import relationship

from database.connection import Base


class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    employees = relationship("Employee", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    age = Column(Integer, nullable=False)
    designation = Column(String(100), nullable=False, index=True)
    salary = Column(Numeric(12, 2), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.department_id"), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    joining_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    department = relationship("Department", back_populates="employees")


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


class User(Base):
    """Login account. Separate from Employee: an Employee is HR data, a User is a credential."""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)   # bcrypt hash, never the password
    role = Column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False, default=UserRole.user, server_default=UserRole.user.value, index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
