from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from database.connection import Base, engine
from database import models  # noqa: F401  (registers tables)
from routes import admin, auth, department, employee, manager, user

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Employee & Department Management API",
    version="2.0.0",
    description=(
        "FastAPI + MySQL with JWT authentication and role-based authorization "
        "(roles: `admin`, `manager`, `user`).\n\n"
        "**Try it in Swagger:** `POST /auth/register` -> `POST /auth/login` -> copy `access_token` "
        "-> click **Authorize** -> paste the token -> call protected endpoints."
    ),
)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)
app.include_router(manager.router)
app.include_router(department.router)
app.include_router(employee.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"),
                "message": e["msg"].removeprefix("Value error, ")}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": details})


@app.exception_handler(SQLAlchemyError)
async def db_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=500, content={"detail": "Database operation failed"})


@app.get("/", tags=["Health"])
def root():
    return {"message": "Employee & Department Management API is running"}
