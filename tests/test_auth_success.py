"""Successful scenarios."""
import jwt

from database.connection import SessionLocal
from database.models import User
from tests.conftest import PASSWORD
from utils.config import settings

NEW_USER = {"name": "Rahul", "email": "rahul@example.com", "password": PASSWORD, "role": "user"}


def test_register_user(client):
    r = client.post("/auth/register", json=NEW_USER)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "rahul@example.com" and body["role"] == "user" and body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_hashed_never_plain(client):
    client.post("/auth/register", json=NEW_USER)
    with SessionLocal() as db:
        stored = db.query(User).filter_by(email="rahul@example.com").one().password_hash
    assert stored != PASSWORD and PASSWORD not in stored
    assert stored.startswith("$2")  # bcrypt


def test_same_password_gets_different_hashes(client):
    client.post("/auth/register", json=NEW_USER)
    client.post("/auth/register", json={**NEW_USER, "email": "other@example.com"})
    with SessionLocal() as db:
        hashes = [u.password_hash for u in db.query(User).all()]
    assert len(set(hashes)) == 2  # per-user salt


def test_email_is_normalised(client):
    r = client.post("/auth/register", json={**NEW_USER, "email": "  RAHUL@Example.COM "})
    assert r.json()["email"] == "rahul@example.com"
    assert client.post("/auth/login", json={"email": "Rahul@EXAMPLE.com", "password": PASSWORD}).status_code == 200


def test_login_returns_bearer_token_with_expected_claims(client):
    client.post("/auth/register", json=NEW_USER)
    r = client.post("/auth/login", json={"email": "rahul@example.com", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 30 * 60
    claims = jwt.decode(body["access_token"], settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert set(claims) >= {"sub", "email", "role", "exp", "iat"}
    assert claims["email"] == "rahul@example.com" and claims["role"] == "user"
    assert claims["exp"] - claims["iat"] == 30 * 60


def test_get_current_user(client, user):
    r = client.get("/auth/me", headers=user)
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"
    assert "password_hash" not in r.json()


def test_full_flow_register_login_me(client):
    """The flow from the assignment, end to end."""
    assert client.post("/auth/register", json=NEW_USER).status_code == 201
    token = client.post("/auth/login", json={"email": NEW_USER["email"], "password": PASSWORD}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["name"] == "Rahul"


def test_protected_endpoint_any_logged_in_user(client, user):
    assert client.get("/departments", headers=user).status_code == 200


def test_admin_can_list_users(client, admin, user):
    r = client.get("/admin/users", headers=admin)
    assert r.status_code == 200
    assert r.json()["total"] == 2
    assert all("password_hash" not in u for u in r.json()["items"])


def test_admin_users_pagination_search_filter_sort(client, admin, make_user):
    for i in range(5):
        make_user(f"u{i}@example.com", "user", f"Person {i}")
    make_user("m@example.com", "manager", "Zed Manager", is_active=False)

    r = client.get("/admin/users?page=1&limit=2", headers=admin).json()
    assert (r["total"], r["total_pages"], len(r["items"])) == (7, 4, 2)

    assert client.get("/admin/users?role=manager", headers=admin).json()["total"] == 1
    assert client.get("/admin/users?is_active=false", headers=admin).json()["total"] == 1
    assert client.get("/admin/users?search=person 3", headers=admin).json()["total"] == 1
    assert client.get("/admin/users?search=u2@", headers=admin).json()["items"][0]["email"] == "u2@example.com"

    names = [u["name"] for u in client.get("/admin/users?sort_by=name&sort_order=desc", headers=admin).json()["items"]]
    assert names == sorted(names, reverse=True)


def test_manager_can_list_users(client, manager):
    assert client.get("/manager/users", headers=manager).status_code == 200
    assert client.get("/users", headers=manager).status_code == 200


def test_admin_can_also_use_manager_api(client, admin):
    assert client.get("/manager/users", headers=admin).status_code == 200


def test_change_password(client, user):
    r = client.patch("/auth/change-password", headers=user,
                     json={"current_password": PASSWORD, "new_password": "NewPassword@456"})
    assert r.status_code == 200
    assert client.post("/auth/login", json={"email": "user@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": "user@example.com", "password": "NewPassword@456"}).status_code == 200


def test_update_own_profile_put_and_patch(client, user, me_id):
    uid = me_id(user)
    r = client.put(f"/users/{uid}", headers=user, json={"name": "New Name", "email": "new@example.com"})
    assert r.status_code == 200 and r.json()["name"] == "New Name"
    r = client.patch(f"/users/{uid}", headers=user, json={"name": "Patched Name"})
    assert r.status_code == 200 and r.json()["name"] == "Patched Name" and r.json()["email"] == "new@example.com"


def test_user_can_view_own_record(client, user, me_id):
    assert client.get(f"/users/{me_id(user)}", headers=user).status_code == 200


def test_admin_manages_any_user(client, admin, user, me_id):
    uid = me_id(user)
    r = client.patch(f"/users/{uid}", headers=admin, json={"role": "manager", "name": "Promoted"})
    assert r.status_code == 200 and r.json()["role"] == "manager"
    assert client.delete(f"/users/{uid}", headers=admin).json()["is_active"] is False
    assert client.patch(f"/users/{uid}", headers=admin, json={"is_active": True}).json()["is_active"] is True


def test_role_change_applies_immediately_to_existing_token(client, admin, user, me_id):
    """Authorization uses the DB role, not the (stale) role claim in the token."""
    assert client.get("/manager/users", headers=user).status_code == 403
    client.patch(f"/users/{me_id(user)}", headers=admin, json={"role": "manager"})
    assert client.get("/manager/users", headers=user).status_code == 200


def test_admin_can_create_manager_via_register(client, admin):
    r = client.post("/auth/register", headers=admin, json={**NEW_USER, "role": "manager"})
    assert r.status_code == 201 and r.json()["role"] == "manager"


def test_openapi_exposes_bearer_scheme_for_swagger_authorize(client):
    spec = client.get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    assert any(s["type"] == "http" and s["scheme"] == "bearer" and s.get("bearerFormat") == "JWT"
               for s in schemes.values())
    assert spec["paths"]["/auth/me"]["get"]["security"]
    assert spec["paths"]["/admin/users"]["get"]["security"]
    assert not spec["paths"]["/auth/login"]["post"].get("security")  # login stays public
