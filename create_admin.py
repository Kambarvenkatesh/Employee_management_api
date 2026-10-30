
import argparse
import getpass
import os
import sys

from fastapi import HTTPException

from database import models  # noqa: F401  (registers tables)
from database.connection import Base, SessionLocal, engine
from database.models import UserRole
from schemas.auth import RegisterRequest
from services import user as user_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[r.value for r in UserRole], default="admin")
    args = parser.parse_args()

    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Password: ")

    try:  # reuse the exact validation rules of POST /auth/register
        data = RegisterRequest(name=args.name, email=args.email, password=password, role=args.role)
    except ValueError as exc:
        print("Invalid input:", exc)
        return 1

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        try:
            user = user_service.create_user(db, name=data.name, email=data.email,
                                            password=data.password, role=data.role)
        except HTTPException as exc:
            print("Error:", exc.detail)
            return 1
        print(f"Created {user.role.value} '{user.name}' <{user.email}> (user_id={user.user_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
