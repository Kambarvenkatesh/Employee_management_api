# Employee & Department Management API (Day 4)

FastAPI + SQLAlchemy 2.0 + MySQL. One Department has many Employees (`employees.department_id` is a foreign key to `departments.department_id`).

## Project structure
```
project/
├── main.py                 # app setup, router registration, global error handlers
├── database/
│   ├── connection.py       # engine, session, get_db dependency
│   └── models.py           # Department & Employee models + relationship
├── schemas/                # Pydantic request/response models (incl. nested)
├── routes/                 # HTTP layer only
├── services/               # business logic, queries, aggregations
├── requirements.txt
└── README.md
```

## Setup
1. Python 3.10+ and MySQL running.
2. Create the database:
   ```sql
   CREATE DATABASE employee_db;
   ```
3. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Set the connection string (or edit the default in `database/connection.py`):
   ```bash
   export DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/employee_db"
   # Windows PowerShell: $env:DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/employee_db"
   ```
5. Run (tables are created automatically on startup):
   ```bash
   uvicorn main:app --reload
   ```
6. Open Swagger UI: http://127.0.0.1:8000/docs

## Endpoints
| Method | Path | Description |
|---|---|---|
| POST | /departments | Create department (unique, non-empty name) |
| GET | /departments | List: `page, limit, search, is_active, sort_by, sort_order` |
| GET | /departments/{id} | Get one (404 if missing) |
| PUT | /departments/{id} | Full update |
| PATCH | /departments/{id} | Partial update |
| DELETE | /departments/{id} | Soft delete (`is_active=false`) |
| GET | /departments/{id}/employees | Employees of a department (pagination, search, sort, active filter) |
| GET | /departments/{id}/summary | Aggregated counts + average salary |
| POST | /employees | Create employee (validates email, salary > 0, age 18-70, department exists) |
| GET | /employees | List: `page, limit, department_id, designation, is_active, search, sort_by, sort_order` |
| GET | /employees/statistics | Totals, active/inactive, avg/max/min salary |
| GET | /employees/{id} | Employee with nested department |
| PUT | /employees/{id} | Full update |
| PATCH | /employees/{id} | Partial update (re-checks department if changed) |
| DELETE | /employees/{id} | Soft delete (extra) |

Sort fields: employees → `name, salary, joining_date, created_at`; departments → `department_name, created_at, department_id`. Sort order: `asc | desc`.
Search on employees matches name, email or designation.

## Status codes
| Case | Code |
|---|---|
| Created | 201 |
| Department / employee not found | 404 |
| Duplicate department name / employee email | 409 |
| Invalid body, salary, age, email, ID, page, limit, sort field/order | 422 |
| PATCH with empty body | 400 |
| Database failure | 500 |

## Invalid test cases to screenshot
Duplicate email (409), duplicate department (409), non-existing department on POST /employees (404), non-existing employee (404), salary 0 (422), age 5 (422), page=0 (422), limit=0 (422), sort_by=age (422), sort_order=up (422), invalid email (422), employee_id=0 (422).

## Useful SQL for the database screenshots
```sql
SHOW TABLES;
DESCRIBE departments;
DESCRIBE employees;
SHOW CREATE TABLE employees;   -- shows the FOREIGN KEY
SELECT * FROM departments;
SELECT * FROM employees;
```
