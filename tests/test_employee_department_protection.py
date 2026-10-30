"""The existing Task 4 endpoints are now protected."""
EMP = {"name": "Asha", "email": "asha@corp.com", "age": 30, "designation": "Engineer",
       "salary": "50000.00", "department_id": 1, "joining_date": "2024-01-15"}


def test_task4_endpoints_reject_anonymous(client):
    assert client.post("/departments", json={"department_name": "HR"}).status_code == 401
    assert client.post("/employees", json=EMP).status_code == 401
    assert client.get("/employees/statistics").status_code == 401


def test_manager_full_task4_flow(client, manager):
    d = client.post("/departments", headers=manager, json={"department_name": "Engineering"})
    assert d.status_code == 201
    e = client.post("/employees", headers=manager, json={**EMP, "department_id": d.json()["department_id"]})
    assert e.status_code == 201
    eid = e.json()["employee_id"]
    assert client.get("/employees", headers=manager).json()["total"] == 1
    assert client.get(f"/employees/{eid}", headers=manager).status_code == 200
    assert client.patch(f"/employees/{eid}", headers=manager, json={"designation": "Lead"}).status_code == 200
    assert client.get("/employees/statistics", headers=manager).status_code == 200
    assert client.get("/departments/1/summary", headers=manager).status_code == 200


def test_normal_user_is_read_only_on_departments_and_blocked_from_salary_data(client, user, manager):
    client.post("/departments", headers=manager, json={"department_name": "Engineering"})
    assert client.get("/departments", headers=user).status_code == 200
    assert client.get("/departments/1", headers=user).status_code == 200
    assert client.post("/departments", headers=user, json={"department_name": "Hack"}).status_code == 403
    assert client.get("/employees", headers=user).status_code == 403
    assert client.get("/employees/statistics", headers=user).status_code == 403
    assert client.get("/departments/1/employees", headers=user).status_code == 403
    assert client.get("/departments/1/summary", headers=user).status_code == 403


def test_delete_is_admin_only(client, manager, admin):
    client.post("/departments", headers=manager, json={"department_name": "Engineering"})
    emp = client.post("/employees", headers=manager, json=EMP).json()
    assert client.delete(f"/employees/{emp['employee_id']}", headers=manager).status_code == 403
    assert client.delete("/departments/1", headers=manager).status_code == 403
    assert client.delete(f"/employees/{emp['employee_id']}", headers=admin).json()["is_active"] is False
    assert client.delete("/departments/1", headers=admin).json()["is_active"] is False


def test_existing_validation_and_404_behaviour_unchanged(client, manager):
    assert client.get("/employees/999", headers=manager).status_code == 404
    assert client.get("/employees/0", headers=manager).status_code == 422
    assert client.get("/employees?page=0", headers=manager).status_code == 422
