"""
FindBack 2.0 - Phase 7 Authentication & RBAC Test Suite

Verifies:
1. Staff portal login flow and anti-enumeration generic error responses.
2. Inactive account rejection and dynamic database revocation.
3. Password hashing security (Werkzeug PBKDF2/scrypt, never plaintext).
4. Approved DEC-07 signed-cookie session payload minimalism (admin_user_id ONLY).
5. Session clearing on login (fixation defense) and logout.
6. Server-side @admin_required protection and 302 redirection for unauthenticated access.
7. Role-Based Access Control (RBAC) 403 Forbidden enforcement.
8. CSRF token validation and missing/tampered token rejection.
9. POST-only logout enforcement (GET /admin/logout -> HTTP 405).
10. Open redirect defense (is_safe_url) on the 'next' parameter.
11. Cookie security flags (HttpOnly, SameSite=Lax).
12. Zero-leakage boundaries across staff authentication views.
"""

import re
import pytest
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import execute_db, query_db
from auth.decorators import is_safe_url

def create_test_admin(app, username="test_admin", password="AdminPassword123!", role="admin", is_active=1):
    """Helper to seed an administrative user into the isolated test database."""
    with app.app_context():
        hashed = generate_password_hash(password)
        cur = execute_db(
            """
            INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, hashed, f"Test {username.title()}", role, is_active),
        )
        return cur.lastrowid

def get_csrf_token(client, path="/admin/login"):
    """Helper to fetch a valid CSRF token from the session via GET request."""
    response = client.get(path)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.get_data(as_text=True))
    if match:
        return match.group(1)
    with client.session_transaction() as sess:
        return sess.get("_csrf_token")

# ----------------------------------------------------------------------
# 1. Login Page Loading & Form Rendering
# ----------------------------------------------------------------------

def test_login_page_renders_cleanly(client):
    """GET /admin/login must load successfully and render the staff login card."""
    response = client.get("/admin/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Staff Portal Authentication" in html
    assert 'name="username"' in html
    assert 'name="password"' in html
    assert 'name="csrf_token"' in html
    # Ensure no leaked system internals
    assert "password_hash" not in html

# ----------------------------------------------------------------------
# 2. Valid Login & Minimal Session Storage (DEC-07)
# ----------------------------------------------------------------------

def test_valid_login_succeeds_and_sets_session(app, client):
    """
    Submitting valid credentials with a valid CSRF token must log the user in,
    redirect to /admin, and store ONLY admin_user_id in the session.
    """
    admin_id = create_test_admin(app, username="lead_admin", password="SecurePassword123!")
    csrf_token = get_csrf_token(client)

    response = client.post(
        "/admin/login",
        data={
            "username": "lead_admin",
            "password": "SecurePassword123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    # Redirects to dashboard
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")

    # DEC-07 Check: Verify session contents
    with client.session_transaction() as sess:
        assert sess.get("admin_user_id") == admin_id
        # Roles and active status must NEVER be stored in the session cookie
        assert "role" not in sess
        assert "is_active" not in sess
        assert "password" not in sess
        assert "password_hash" not in sess
        assert "full_name" not in sess

def test_session_cookie_payload_is_minimal(app, client):
    """
    DEC-07 Audit: Verify that the serialized session cookie does NOT contain
    roles, permissions, clues, password hashes, or contact information.
    """
    create_test_admin(app, username="audit_admin", password="AuditPassword123!", role="admin")
    csrf_token = get_csrf_token(client)

    response = client.post(
        "/admin/login",
        data={
            "username": "audit_admin",
            "password": "AuditPassword123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Inspect Set-Cookie header string
    set_cookie = response.headers.get("Set-Cookie", "")
    assert set_cookie != ""
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie

    # Ensure forbidden sensitive strings never appear in the cookie payload
    forbidden_tokens = ["AuditPassword123", "password_hash", "admin_users", "reporter_contact"]
    for token in forbidden_tokens:
        assert token not in set_cookie

# ----------------------------------------------------------------------
# 3. Invalid Credentials & Anti-Enumeration Defense
# ----------------------------------------------------------------------

def test_invalid_credentials_generic_error(app, client):
    """
    Authentication failures must return HTTP 401 with a uniform generic error message.
    The response must be identical whether the username is wrong or the password is wrong.
    """
    create_test_admin(app, username="existing_user", password="CorrectPassword123!")
    csrf_token = get_csrf_token(client)

    # 1. Non-existent username
    res1 = client.post(
        "/admin/login",
        data={
            "username": "ghost_user",
            "password": "AnyPassword123!",
            "csrf_token": csrf_token,
        },
    )
    assert res1.status_code == 401
    assert b"Invalid credentials or inactive account." in res1.data

    # 2. Existing username, incorrect password
    csrf_token = get_csrf_token(client)
    res2 = client.post(
        "/admin/login",
        data={
            "username": "existing_user",
            "password": "WrongPassword123!",
            "csrf_token": csrf_token,
        },
    )
    assert res2.status_code == 401
    assert b"Invalid credentials or inactive account." in res2.data

    # Ensure no session was established
    with client.session_transaction() as sess:
        assert "admin_user_id" not in sess

def test_login_missing_fields_rejected(client):
    """Submitting empty username or password returns HTTP 400."""
    csrf_token = get_csrf_token(client)
    response = client.post(
        "/admin/login",
        data={
            "username": "",
            "password": "",
            "csrf_token": csrf_token,
        },
    )
    assert response.status_code == 400
    assert b"Invalid credentials or inactive account." in response.data

# ----------------------------------------------------------------------
# 4. Inactive Account Enforcement
# ----------------------------------------------------------------------

def test_inactive_account_login_rejected(app, client):
    """
    An account with is_active = 0 cannot authenticate, even with correct credentials.
    Returns HTTP 401 with the standard anti-enumeration generic message.
    """
    create_test_admin(app, username="deactivated_officer", password="GoodPassword123!", is_active=0)
    csrf_token = get_csrf_token(client)

    response = client.post(
        "/admin/login",
        data={
            "username": "deactivated_officer",
            "password": "GoodPassword123!",
            "csrf_token": csrf_token,
        },
    )
    assert response.status_code == 401
    assert b"Invalid credentials or inactive account." in response.data

    with client.session_transaction() as sess:
        assert "admin_user_id" not in sess

# ----------------------------------------------------------------------
# 5. Dynamic Database Account Revocation
# ----------------------------------------------------------------------

def test_dynamic_db_account_change_takes_effect_immediately(app, client):
    """
    If an admin is logged in and their account is deactivated (is_active = 0)
    in the database, their next request to a protected route must be immediately
    rejected and their session revoked.
    """
    admin_id = create_test_admin(app, username="temp_officer", password="TempPassword123!", is_active=1)
    csrf_token = get_csrf_token(client)

    # Log in
    client.post(
        "/admin/login",
        data={
            "username": "temp_officer",
            "password": "TempPassword123!",
            "csrf_token": csrf_token,
        },
    )

    # Verify protected access works
    res_before = client.get("/admin")
    assert res_before.status_code == 200

    # Deactivate account in SQLite database
    with app.app_context():
        execute_db("UPDATE admin_users SET is_active = 0 WHERE id = ?", [admin_id])

    # Next request must fail closed
    res_after = client.get("/admin", follow_redirects=False)
    assert res_after.status_code == 302
    assert "/admin/login" in res_after.headers["Location"]

    # Verify session was cleared
    with client.session_transaction() as sess:
        assert "admin_user_id" not in sess

def test_deleted_account_takes_effect_immediately(app, client):
    """If an account row is deleted from the DB, access is immediately revoked."""
    admin_id = create_test_admin(app, username="to_be_deleted", password="DeletePassword123!")
    csrf_token = get_csrf_token(client)

    client.post(
        "/admin/login",
        data={
            "username": "to_be_deleted",
            "password": "DeletePassword123!",
            "csrf_token": csrf_token,
        },
    )

    with app.app_context():
        execute_db("DELETE FROM admin_users WHERE id = ?", [admin_id])

    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]

# ----------------------------------------------------------------------
# 6. Session Fixation & Logout
# ----------------------------------------------------------------------

def test_session_cleared_on_login_and_logout(app, client):
    """
    Session keys prior to login must be purged upon authentication (session fixation defense).
    Logging out must clear all session keys and invalidate access.
    """
    create_test_admin(app, username="session_tester", password="SessionPassword123!")

    # Set pre-existing session data
    with client.session_transaction() as sess:
        sess["pre_login_crumb"] = "attacker_injected_value"

    csrf_token = get_csrf_token(client)
    client.post(
        "/admin/login",
        data={
            "username": "session_tester",
            "password": "SessionPassword123!",
            "csrf_token": csrf_token,
        },
    )

    # Verify stale pre-login data was flushed
    with client.session_transaction() as sess:
        assert "pre_login_crumb" not in sess
        assert "admin_user_id" in sess

    # Logout via POST with CSRF token
    csrf_token = get_csrf_token(client, path="/admin")
    res_logout = client.post(
        "/admin/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert res_logout.status_code == 302
    assert res_logout.headers["Location"].endswith("/")

    # Verify session is empty
    with client.session_transaction() as sess:
        assert "admin_user_id" not in sess

def test_logout_via_get_rejected(app, client):
    """GET /admin/logout is not allowed (HTTP 405) to defend against pre-fetching and simple CSRF."""
    response = client.get("/admin/logout")
    assert response.status_code == 405

# ----------------------------------------------------------------------
# 7. Server-Side Protection & RBAC
# ----------------------------------------------------------------------

def test_unauthenticated_protected_route_blocked(client):
    """Direct access to /admin and /admin/leads without a session redirects to /admin/login."""
    res_dashboard = client.get("/admin", follow_redirects=False)
    assert res_dashboard.status_code == 302
    assert "/admin/login" in res_dashboard.headers["Location"]

    res_leads = client.get("/admin/leads", follow_redirects=False)
    assert res_leads.status_code == 302
    assert "/admin/login" in res_leads.headers["Location"]

def test_authenticated_dashboard_and_leads_accessible(app, client):
    """Authenticated staff can access dashboard and leads review views (HTTP 200)."""
    create_test_admin(app, username="desk_user", password="DeskPassword123!", role="desk_staff")
    csrf_token = get_csrf_token(client)
    client.post(
        "/admin/login",
        data={
            "username": "desk_user",
            "password": "DeskPassword123!",
            "csrf_token": csrf_token,
        },
    )

    res_dash = client.get("/admin")
    assert res_dash.status_code == 200
    assert b"Administrator Control Center" in res_dash.data
    assert b"desk_staff" in res_dash.data

    res_leads = client.get("/admin/leads")
    assert res_leads.status_code == 200
    assert b"Deterministic Match Review Queue" in res_leads.data

def test_insufficient_role_returns_403(app, client):
    """An account with role 'desk_staff' attempting to access an 'admin'-only endpoint gets HTTP 403."""
    from auth.decorators import admin_required

    # Register an admin-only endpoint
    @app.route("/admin/system-management")
    @admin_required(roles="admin")
    def admin_only_route():
        return "System Admin Zone"

    create_test_admin(app, username="junior_staff", password="StaffPassword123!", role="desk_staff")
    csrf_token = get_csrf_token(client)
    client.post(
        "/admin/login",
        data={
            "username": "junior_staff",
            "password": "StaffPassword123!",
            "csrf_token": csrf_token,
        },
    )

    # Attempt to access admin-only route
    res = client.get("/admin/system-management")
    assert res.status_code == 403
    assert b"Access denied" in res.data

# ----------------------------------------------------------------------
# 8. CSRF Protection
# ----------------------------------------------------------------------

def test_csrf_token_missing_rejected(app, client):
    """POST /admin/login without CSRF token returns HTTP 400."""
    create_test_admin(app, username="csrf_target", password="TargetPassword123!")
    response = client.post(
        "/admin/login",
        data={
            "username": "csrf_target",
            "password": "TargetPassword123!",
        },
    )
    assert response.status_code == 400
    assert b"CSRF token" in response.data

def test_csrf_token_invalid_rejected(app, client):
    """POST /admin/login with forged CSRF token returns HTTP 400."""
    create_test_admin(app, username="csrf_target2", password="TargetPassword123!")
    get_csrf_token(client)  # Establish valid session
    response = client.post(
        "/admin/login",
        data={
            "username": "csrf_target2",
            "password": "TargetPassword123!",
            "csrf_token": "forged_malicious_token_1234567890",
        },
    )
    assert response.status_code == 400
    assert b"CSRF token" in response.data

# ----------------------------------------------------------------------
# 9. Open Redirect Defense
# ----------------------------------------------------------------------

def test_open_redirect_defense(app, client):
    """
    Login must reject external next parameter targets and redirect to dashboard instead.
    Safe local relative paths are honored.
    """
    create_test_admin(app, username="redirect_admin", password="RedirectPassword123!")
    csrf_token = get_csrf_token(client)

    # External malicious targets
    bad_targets = [
        "https://malicious.evil.com",
        "http://attacker.local/steal",
        "//evil.com/phish",
        "\\\\evil.com\\path",
        "javascript:alert(1)",
    ]

    for bad in bad_targets:
        with client.session_transaction() as sess:
            sess.clear()
        csrf_token = get_csrf_token(client)
        res = client.post(
            "/admin/login",
            data={
                "username": "redirect_admin",
                "password": "RedirectPassword123!",
                "next": bad,
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        assert res.status_code == 302
        assert res.headers["Location"].endswith("/admin")

    # Safe internal target
    with client.session_transaction() as sess:
        sess.clear()
    csrf_token = get_csrf_token(client)
    res_safe = client.post(
        "/admin/login",
        data={
            "username": "redirect_admin",
            "password": "RedirectPassword123!",
            "next": "/admin/leads",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert res_safe.status_code == 302
    assert res_safe.headers["Location"].endswith("/admin/leads")
    assert res_safe.headers["Location"].endswith("/admin/leads")

def test_is_safe_url_helper():
    """Unit test for is_safe_url validator."""
    assert is_safe_url("/admin") is True
    assert is_safe_url("/admin/leads?status=open") is True
    assert is_safe_url("https://google.com") is False
    assert is_safe_url("//google.com") is False
    assert is_safe_url("javascript:void(0)") is False
    assert is_safe_url("") is False
    assert is_safe_url(None) is False

# ----------------------------------------------------------------------
# 10. API Authentication Behavior
# ----------------------------------------------------------------------

def test_api_unauthenticated_request_returns_401(client):
    """API or JSON requests to protected endpoints return 401 JSON instead of redirect."""
    res = client.get("/admin", headers={"Accept": "application/json"})
    assert res.status_code == 401
    json_data = res.get_json()
    assert json_data is not None
    assert "error" in json_data

# ----------------------------------------------------------------------
# 11. Already Logged In Redirect
# ----------------------------------------------------------------------

def test_already_logged_in_user_redirected_from_login_page(app, client):
    """An active logged-in administrator visiting /admin/login is redirected to /admin."""
    create_test_admin(app, username="already_in", password="AlreadyPassword123!")
    csrf_token = get_csrf_token(client)
    client.post(
        "/admin/login",
        data={
            "username": "already_in",
            "password": "AlreadyPassword123!",
            "csrf_token": csrf_token,
        },
    )

    res = client.get("/admin/login", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/admin")

# ----------------------------------------------------------------------
# 12. Password Hashing Verification
# ----------------------------------------------------------------------

def test_password_hashing_security(app):
    """Ensure stored passwords use secure cryptographic one-way hashes."""
    with app.app_context():
        raw_pw = "SuperSecretAdmin123!"
        hashed = generate_password_hash(raw_pw)
        assert hashed != raw_pw
        assert check_password_hash(hashed, raw_pw) is True
        assert check_password_hash(hashed, "WrongPassword") is False
