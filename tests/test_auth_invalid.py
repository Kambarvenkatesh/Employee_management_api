"""Invalid / negative scenarios (more than the 12 required)."""
from datetime import timedelta

import jwt
import pytest

from database.connection import SessionLocal
from database.models import User
from tests.conftest import PASSWORD
from utils.config import settings
from utils.jwt import create_access_token

GOOD = {"name": "Rahul", "email": "rahul@example.com", "password": PASSWORD, "role": "user"}


# ---------- registration ----------
def test_01_duplicate_email(client):
    assert client.post("/auth/register", json=GOOD).status_code == 201
    r = client.post("/auth/register", json={**GOOD, "email": "RAHUL@example.com"})  # case-insensitive
    assert r.status_code == 409


def test_02_invalid_email(client):
    r = client.post("/auth/register", json={**GOOD, "email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.parametrize("bad, expected_fragment", [
    ("Sh0rt!", "at least 8"),
    ("password@123", "uppercase"),
    ("PASSWORD@123", "lowercase"),
    ("Password@abc", "number"),
    ("Password1234", "special"),
    ("A1!" + "a" * 80, "at most 72"),
])
def test_03_weak_password(client, bad, expected_fragment):
    r = client.post("/auth/register", json={**GOOD, "password": bad})
    assert r.status_code == 422
    assert expected_fragment in r.text


def test_04_invalid_name(client):
    for bad in ["", " ", "A", "x" * 101]:
        assert client.post("/auth/register", json={**GOOD, "name": bad}).status_code == 422


def test_05_invalid_role(client):
    r = client.post("/auth/register", json={**GOOD, "role": "superuser"})
    assert r.status_code == 422


def test_06_missing_fields_invalid_body(client):
    assert client.post("/auth/register", json={"email": "a@b.com"}).status_code == 422
    assert client.post("/auth/register", content="not json", headers={"Content-Type": "application/json"}).status_code == 422


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_07_public_register_cannot_pick_privileged_role(client, role):
    r = client.post("/auth/register", json={**GOOD, "role": role})
    assert r.status_code == 403
    with SessionLocal() as db:
        assert db.query(User).count() == 0


def test_07b_normal_user_token_cannot_create_privileged_role(client, user):
    assert client.post("/auth/register", headers=user, json={**GOOD, "role": "admin"}).status_code == 403


# ---------- login ----------
def test_08_wrong_password(client, user):
    r = client.post("/auth/login", json={"email": "user@example.com", "password": "Wrong@12345"})
    assert r.status_code == 401


def test_09_unknown_email_looks_identical_to_wrong_password(client, user):
    wrong_pw = client.post("/auth/login", json={"email": "user@example.com", "password": "Wrong@12345"})
    wrong_email = client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong_email.status_code == wrong_pw.status_code == 401
    assert wrong_email.json() == wrong_pw.json()  # nothing reveals which field was wrong


def test_10_login_invalid_body(client):
    assert client.post("/auth/login", json={"email": "bad", "password": "x"}).status_code == 422
    assert client.post("/auth/login", json={"email": "a@b.com"}).status_code == 422


def test_11_inactive_user_cannot_login(client, make_user):
    make_user("gone@example.com", is_active=False)
    r = client.post("/auth/login", json={"email": "gone@example.com", "password": PASSWORD})
    assert r.status_code == 403


# ---------- tokens ----------
@pytest.mark.parametrize("path", ["/auth/me", "/users", "/admin/users", "/manager/users", "/employees", "/departments"])
def test_12_missing_token(client, path):
    r = client.get(path)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_13_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer this.is.garbage"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid token"


def test_14_token_signed_with_wrong_secret(client, user):
    forged = jwt.encode({"sub": "1", "role": "admin", "exp": 9999999999}, "attacker-secret-key-0123456789abcdef", algorithm="HS256")
    assert client.get("/admin/users", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_15_alg_none_token_rejected(client, user):
    forged = jwt.encode({"sub": "1", "role": "admin", "exp": 9999999999}, None, algorithm="none")
    assert client.get("/admin/users", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_16_expired_token(client, make_user):
    uid = make_user("exp@example.com")
    with SessionLocal() as db:
        u = db.get(User, uid)
        token = create_access_token(u, expires_delta=timedelta(seconds=-5))
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and r.json()["detail"] == "Token has expired"


def test_17_token_without_exp_rejected(client, make_user):
    uid = make_user("noexp@example.com")
    token = jwt.encode({"sub": str(uid)}, settings.JWT_SECRET_KEY, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_18_token_for_deleted_user(client, make_user):
    uid = make_user("ghost@example.com")
    with SessionLocal() as db:
        u = db.get(User, uid)
        token = create_access_token(u)
        db.delete(u)
        db.commit()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_19_wrong_auth_scheme(client, user):
    token = user["Authorization"].split()[1]
    assert client.get("/auth/me", headers={"Authorization": f"Basic {token}"}).status_code == 401


def test_20_user_deactivated_after_login_is_locked_out(client, admin, user, me_id):
    client.delete(f"/users/{me_id(user)}", headers=admin)
    r = client.get("/auth/me", headers=user)  # same, still-unexpired token
    assert r.status_code == 403 and r.json()["detail"] == "Inactive user"


# ---------- role-based authorization ----------
def test_21_user_cannot_access_admin_api(client, user):
    assert client.get("/admin/users", headers=user).status_code == 403


def test_22_manager_cannot_access_admin_api(client, manager):
    assert client.get("/admin/users", headers=manager).status_code == 403


def test_23_user_cannot_access_manager_api(client, user):
    assert client.get("/manager/users", headers=user).status_code == 403
    assert client.get("/users", headers=user).status_code == 403


def test_24_user_cannot_view_or_modify_other_users(client, user, admin, me_id):
    other = me_id(admin)
    assert client.get(f"/users/{other}", headers=user).status_code == 403
    assert client.put(f"/users/{other}", headers=user, json={"name": "Hacked", "email": "h@example.com"}).status_code == 403
    assert client.patch(f"/users/{other}", headers=user, json={"name": "Hacked"}).status_code == 403
    assert client.delete(f"/users/{other}", headers=user).status_code == 403


def test_25_manager_cannot_modify_other_users(client, manager, user, me_id):
    assert client.patch(f"/users/{me_id(user)}", headers=manager, json={"name": "Nope"}).status_code == 403
    assert client.delete(f"/users/{me_id(user)}", headers=manager).status_code == 403


def test_26_user_cannot_escalate_own_role(client, user, me_id):
    uid = me_id(user)
    assert client.patch(f"/users/{uid}", headers=user, json={"role": "admin"}).status_code == 403
    assert client.get("/auth/me", headers=user).json()["role"] == "user"


def test_27_user_cannot_reactivate_or_change_active_flag(client, user, me_id):
    assert client.patch(f"/users/{me_id(user)}", headers=user, json={"is_active": False}).status_code == 403


def test_28_non_admin_gets_403_even_for_nonexistent_user(client, user):
    """No user-enumeration: 403 for a missing id, same as for an existing one."""
    assert client.get("/users/99999", headers=user).status_code == 403


# ---------- user management ----------
def test_29_user_not_found(client, admin):
    assert client.get("/users/99999", headers=admin).status_code == 404
    assert client.patch("/users/99999", headers=admin, json={"name": "Ghost"}).status_code == 404
    assert client.delete("/users/99999", headers=admin).status_code == 404


def test_30_invalid_user_id_and_empty_patch(client, admin, me_id):
    assert client.get("/users/0", headers=admin).status_code == 422
    assert client.get("/users/abc", headers=admin).status_code == 422
    assert client.patch(f"/users/{me_id(admin)}", headers=admin, json={}).status_code == 400
    assert client.patch(f"/users/{me_id(admin)}", headers=admin, json={"name": None}).status_code == 422


def test_31_update_to_existing_email_conflicts(client, admin, user, me_id):
    r = client.patch(f"/users/{me_id(user)}", headers=user, json={"email": "admin@example.com"})
    assert r.status_code == 409


def test_32_admin_cannot_deactivate_or_demote_self(client, admin, me_id):
    aid = me_id(admin)
    assert client.delete(f"/users/{aid}", headers=admin).status_code == 400
    assert client.patch(f"/users/{aid}", headers=admin, json={"role": "user"}).status_code == 400
    assert client.patch(f"/users/{aid}", headers=admin, json={"is_active": False}).status_code == 400


def test_33_bad_list_query_params(client, admin):
    for q in ["page=0", "limit=0", "limit=101", "role=boss", "sort_by=password_hash", "sort_order=up", "is_active=maybe"]:
        assert client.get(f"/admin/users?{q}", headers=admin).status_code == 422, q


# ---------- change password ----------
def test_34_change_password_wrong_current(client, user):
    r = client.patch("/auth/change-password", headers=user,
                     json={"current_password": "Wrong@12345", "new_password": "NewPassword@456"})
    assert r.status_code == 400


def test_35_change_password_weak_new(client, user):
    r = client.patch("/auth/change-password", headers=user,
                     json={"current_password": PASSWORD, "new_password": "weak"})
    assert r.status_code == 422


def test_36_change_password_same_as_current(client, user):
    r = client.patch("/auth/change-password", headers=user,
                     json={"current_password": PASSWORD, "new_password": PASSWORD})
    assert r.status_code == 400


def test_37_change_password_requires_auth(client):
    r = client.patch("/auth/change-password", json={"current_password": PASSWORD, "new_password": "NewPassword@456"})
    assert r.status_code == 401


def test_38_failed_change_leaves_password_unchanged(client, user):
    client.patch("/auth/change-password", headers=user,
                 json={"current_password": "Wrong@12345", "new_password": "NewPassword@456"})
    assert client.post("/auth/login", json={"email": "user@example.com", "password": PASSWORD}).status_code == 200
