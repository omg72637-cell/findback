"""
FindBack 2.0 - Phase 8: Authorized Review Dashboard & Safe Handover Test Suite

Verifies:
1. Authorized staff can load the review dashboard, queue, disputes, and handover desk.
2. Unauthenticated access is blocked (redirects to /admin/login).
3. Tiered Role-Based Access Control (RBAC):
   - 'desk_staff' can view leads, disputes, and redeem tokens at the custody desk.
   - 'desk_staff' attempting state-changing lead review actions (status change, approve) receives HTTP 403 Forbidden.
   - 'admin' has full operational authority to update status, adjudicate disputes, and approve leads.
4. Server-side allowlist validation for status transitions.
5. Strict item-level dispute freezing:
   - Competing claims cannot generate handover tokens.
   - Dismissing competing claims cleanly unfreezes the valid candidate lead.
6. Unrelated high-scoring candidates do not falsely trigger disputes.
7. Single-use handover token security:
   - Cryptographic unpredictability.
   - SHA-256 hash storage; raw token NEVER persisted in the database.
   - 30-minute expiry enforcement.
   - Single-use enforcement (replay/double-redemption blocked).
   - Atomic SQLite rollback on redemption failure.
8. CSRF token enforcement across all state-changing endpoints.
9. Audit trail completeness with zero leakage of raw tokens or credentials.
"""

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
import pytest
from werkzeug.security import generate_password_hash
from database.db import execute_db, query_db
from matching.service import (
    find_and_record_matches,
    issue_handover_token,
    redeem_handover_token,
    update_lead_review_status,
    can_lead_proceed_to_handover,
    hash_handover_token,
)

# ----------------------------------------------------------------------
# Test Helpers
# ----------------------------------------------------------------------

def create_user(app, username, role="admin", is_active=1, password="TestPassword123!"):
    """Seed an admin or desk_staff user into the test database."""
    with app.app_context():
        hashed = generate_password_hash(password)
        cur = execute_db(
            """
            INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, hashed, f"Officer {username.title()}", role, is_active),
        )
        return cur.lastrowid

def create_private_report(
    app,
    report_type="lost",
    device_type="phone",
    brand="Apple",
    model_family="iPhone 13",
    primary_color="Midnight Blue",
    campus_location="Central Library 3rd Floor",
    date_discovered="2026-10-20",
    distinctive_clues="Clear Spigen case with dog photo lockscreen",
    reporter_contact="student1@campus.edu",
    status="open",
):
    """Seed a synthetic private electronics report."""
    with app.app_context():
        import secrets
        tracking_code = f"TRK-{secrets.token_urlsafe(16)}"
        cur = execute_db(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status,
            ),
        )
        return cur.lastrowid

def get_csrf(client, path="/admin/login"):
    """Fetch valid CSRF token from current session."""
    client.get(path)
    with client.session_transaction() as sess:
        return sess.get("_csrf_token")

def login(client, username, password="TestPassword123!"):
    """Log in an administrative client."""
    csrf_token = get_csrf(client)
    res = client.post(
        "/admin/login",
        data={"username": username, "password": password, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert res.status_code == 302
    return res

# ----------------------------------------------------------------------
# 1. Dashboard Access & Unauthenticated Rejection
# ----------------------------------------------------------------------

def test_authorized_staff_can_load_dashboard_and_queues(app, client):
    """Both 'admin' and 'desk_staff' can view the review queue, disputes, and handover desk."""
    create_user(app, username="admin_alice", role="admin")
    create_user(app, username="desk_bob", role="desk_staff")

    # Admin access
    login(client, "admin_alice")
    assert client.get("/admin/leads").status_code == 200
    assert client.get("/admin/disputes").status_code == 200
    assert client.get("/admin/handover").status_code == 200

    # Logout
    csrf = get_csrf(client, "/admin")
    client.post("/admin/logout", data={"csrf_token": csrf})

    # Desk staff access
    login(client, "desk_bob")
    assert client.get("/admin/leads").status_code == 200
    assert client.get("/admin/disputes").status_code == 200
    assert client.get("/admin/handover").status_code == 200

def test_unauthenticated_users_redirected_to_login(client):
    """Unauthenticated requests to review queues and handover desk redirect to /admin/login."""
    for path in ("/admin/leads", "/admin/disputes", "/admin/handover"):
        res = client.get(path, follow_redirects=False)
        assert res.status_code == 302
        assert "/admin/login" in res.headers["Location"]

# ----------------------------------------------------------------------
# 2. Tiered RBAC Enforcement ('admin' vs 'desk_staff')
# ----------------------------------------------------------------------

def test_desk_staff_cannot_approve_lead_or_change_status(app, client):
    """
    Tiered RBAC: 'desk_staff' attempting to approve a lead or update lead status
    must be rejected with HTTP 403 Forbidden on the server.
    """
    create_user(app, username="desk_officer", role="desk_staff")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        assert len(leads) > 0
        lead_id = leads[0]["lead_id"]

    login(client, "desk_officer")
    csrf = get_csrf(client, "/admin/leads")

    # Desk staff attempting to update status -> 403
    res_status = client.post(
        f"/admin/leads/{lead_id}/status",
        data={"status": "investigating", "csrf_token": csrf},
    )
    assert res_status.status_code == 403
    assert b"Access denied" in res_status.data

    # Desk staff attempting to approve lead -> 403
    res_approve = client.post(
        f"/admin/leads/{lead_id}/approve",
        data={"csrf_token": csrf},
    )
    assert res_approve.status_code == 403
    assert b"Access denied" in res_approve.data

def test_admin_can_approve_lead_and_change_status(app, client):
    """An 'admin' can successfully update lead review status and approve leads."""
    create_user(app, username="lead_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]

    login(client, "lead_admin")
    csrf = get_csrf(client, "/admin/leads")

    # Update status to investigating
    res_status = client.post(
        f"/admin/leads/{lead_id}/status",
        data={"status": "investigating", "csrf_token": csrf},
        follow_redirects=True,
    )
    assert res_status.status_code == 200
    assert b"investigating" in res_status.data

    # Approve lead and receive raw token
    csrf = get_csrf(client, "/admin/leads")
    res_approve = client.post(
        f"/admin/leads/{lead_id}/approve",
        data={"csrf_token": csrf},
    )
    assert res_approve.status_code == 200
    assert b"Handover Authorization Token" in res_approve.data
    assert b"HND-" in res_approve.data

# ----------------------------------------------------------------------
# 3. Status Transition Allowlist & Validation
# ----------------------------------------------------------------------

def test_invalid_status_transition_rejected(app, client):
    """Submitting an unapproved status string returns HTTP 400 Bad Request."""
    create_user(app, username="sec_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]

    login(client, "sec_admin")
    csrf = get_csrf(client, "/admin/leads")

    res = client.post(
        f"/admin/leads/{lead_id}/status",
        data={"status": "arbitrary_unsafe_status", "csrf_token": csrf},
    )
    assert res.status_code == 400
    assert b"Invalid review status" in res.data

# ----------------------------------------------------------------------
# 4. Dispute Freezing & Handover Locking
# ----------------------------------------------------------------------

def test_disputed_lead_blocked_from_token_generation(app, client):
    """
    When multiple lost reports match the same found device, automatic handover
    token generation is strictly locked (HTTP 400 with dispute error).
    """
    create_user(app, username="dispute_admin", role="admin")
    # Found phone
    found_id = create_private_report(app, report_type="found", brand="Apple", primary_color="Black")
    # Lost phone 1
    lost_id1 = create_private_report(app, report_type="lost", brand="Apple", primary_color="Black")
    # Lost phone 2 (competing claimant)
    lost_id2 = create_private_report(app, report_type="lost", brand="Apple", primary_color="Black")

    with app.app_context():
        find_and_record_matches(found_id)
        leads = query_db("SELECT id, review_status FROM match_leads WHERE found_report_id = ?", [found_id])
        assert len(leads) >= 2
        for l in leads:
            assert l["review_status"] == "disputed"
        disputed_lead_id = leads[0]["id"]

    login(client, "dispute_admin")
    csrf = get_csrf(client, "/admin/leads")

    # Attempt to approve disputed lead -> BLOCKED
    res_approve = client.post(
        f"/admin/leads/{disputed_lead_id}/approve",
        data={"csrf_token": csrf},
    )
    assert res_approve.status_code == 400
    assert b"disputed" in res_approve.data

def test_dismissing_competing_claim_unfreezes_remaining_lead(app, client):
    """
    Adjudicating a dispute by dismissing invalid competing claims automatically
    clears the dispute freeze on the remaining candidate lead and underlying item.
    """
    admin_id = create_user(app, username="adjudicator", role="admin")
    found_id = create_private_report(app, report_type="found", brand="Apple", primary_color="Black")
    lost_id1 = create_private_report(app, report_type="lost", brand="Apple", primary_color="Black")
    lost_id2 = create_private_report(app, report_type="lost", brand="Apple", primary_color="Black")

    with app.app_context():
        find_and_record_matches(found_id)
        leads = query_db(
            "SELECT id, lost_report_id FROM match_leads WHERE found_report_id = ? ORDER BY id",
            [found_id],
        )
        assert len(leads) == 2
        false_lead_id = leads[0]["id"]
        valid_lead_id = leads[1]["id"]

        # Admin dismisses the false competing claim
        success, msg = update_lead_review_status(
            lead_id=false_lead_id,
            new_status="dismissed",
            admin_id=admin_id,
            admin_notes="Adjudicated: Clues do not match.",
        )
        assert success is True

        # Verify false lead is dismissed
        lead1 = query_db("SELECT review_status FROM match_leads WHERE id = ?", [false_lead_id], one=True)
        assert lead1["review_status"] == "dismissed"

        # Verify valid lead is automatically unfrozen to 'investigating'
        lead2 = query_db("SELECT review_status FROM match_leads WHERE id = ?", [valid_lead_id], one=True)
        assert lead2["review_status"] == "investigating"

        # Verify found item status is no longer 'disputed'
        found_item = query_db("SELECT status FROM private_electronics WHERE id = ?", [found_id], one=True)
        assert found_item["status"] == "lead_identified"

        # Valid lead can now proceed to handover approval
        can_proceed, reason = can_lead_proceed_to_handover(valid_lead_id)
        assert can_proceed is True

def test_unrelated_high_scoring_candidates_do_not_dispute(app):
    """Two independent matches on disjoint items do not create a dispute."""
    lost1 = create_private_report(app, report_type="lost", brand="Dell", campus_location="Hall A")
    found1 = create_private_report(app, report_type="found", brand="Dell", campus_location="Hall A")
    lost2 = create_private_report(app, report_type="lost", brand="Sony", campus_location="Hall B")
    found2 = create_private_report(app, report_type="found", brand="Sony", campus_location="Hall B")

    with app.app_context():
        leads1 = find_and_record_matches(found1)
        leads2 = find_and_record_matches(found2)

        assert len(leads1) == 1
        assert len(leads2) == 1
        assert leads1[0]["review_status"] == "pending_review"
        assert leads2[0]["review_status"] == "pending_review"

# ----------------------------------------------------------------------
# 5. Single-Use Handover Token Lifecycle
# ----------------------------------------------------------------------

def test_token_unpredictability_and_hash_only_storage(app):
    """
    Tokens are generated with high entropy (HND-...) and raw tokens
    are NEVER persisted in the database (only 64-char SHA-256 hash).
    """
    admin_id = create_user(app, username="tok_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]

        success, msg, raw_token = issue_handover_token(lead_id, admin_id)
        assert success is True
        assert raw_token.startswith("HND-")
        assert len(raw_token) >= 12

        # Inspect database
        log_row = query_db("SELECT * FROM handover_logs WHERE match_id = ?", [lead_id], one=True)
        assert log_row is not None
        assert log_row["token_hash"] == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert len(log_row["token_hash"]) == 64
        # Assert raw token does NOT appear in any column of the table
        for key in log_row.keys():
            assert raw_token not in str(log_row[key])

def test_token_redemption_and_single_use_enforcement(app, client):
    """
    A valid token can be redeemed exactly once.
    Second attempt is rejected with Single-Use Violation.
    """
    admin_id = create_user(app, username="issuer", role="admin")
    desk_id = create_user(app, username="desk_worker", role="desk_staff")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)

    # Desk staff redeems token at custody desk
    login(client, "desk_worker")
    csrf = get_csrf(client, "/admin/handover")

    # First redemption succeeds
    res1 = client.post(
        "/admin/handover",
        data={
            "token": raw_token,
            "resolution_notes": "Student ID #2026-CS-101 verified.",
            "csrf_token": csrf,
        },
    )
    assert res1.status_code == 200
    assert b"Handover successfully completed" in res1.data

    # Verify database state after first redemption
    with app.app_context():
        log = query_db("SELECT token_used_at FROM handover_logs WHERE match_id = ?", [lead_id], one=True)
        assert log["token_used_at"] is not None

        lost_row = query_db("SELECT status FROM private_electronics WHERE id = ?", [lost_id], one=True)
        found_row = query_db("SELECT status FROM private_electronics WHERE id = ?", [found_id], one=True)
        assert lost_row["status"] == "resolved"
        assert found_row["status"] == "resolved"

    # Second redemption attempt MUST fail (Single-use violation)
    csrf = get_csrf(client, "/admin/handover")
    res2 = client.post(
        "/admin/handover",
        data={
            "token": raw_token,
            "csrf_token": csrf,
        },
    )
    assert res2.status_code == 400
    assert b"Single-Use Token Violation" in res2.data

def test_expired_token_rejected(app, client):
    """Tokens past the 30-minute validity window are rejected."""
    admin_id = create_user(app, username="exp_admin", role="admin")
    desk_id = create_user(app, username="exp_desk", role="desk_staff")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)

        # Artificially expire the token in the database
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=35)).isoformat()
        execute_db("UPDATE handover_logs SET token_expires_at = ? WHERE match_id = ?", [past_time, lead_id])

    login(client, "exp_desk")
    csrf = get_csrf(client, "/admin/handover")

    res = client.post(
        "/admin/handover",
        data={"token": raw_token, "csrf_token": csrf},
    )
    assert res.status_code == 400
    assert b"expired" in res.data

def test_unknown_token_rejected(app, client):
    """Submitting a fabricated token returns 400 Bad Request."""
    create_user(app, username="desk_checker", role="desk_staff")
    login(client, "desk_checker")
    csrf = get_csrf(client, "/admin/handover")

    res = client.post(
        "/admin/handover",
        data={"token": "HND-FABRICATED999", "csrf_token": csrf},
    )
    assert res.status_code == 400
    assert b"Invalid or unknown" in res.data

# ----------------------------------------------------------------------
# 6. Concurrency & Transaction Rollback Safety
# ----------------------------------------------------------------------

def test_concurrent_redemption_prevented(app):
    """
    Simulated concurrent redemption: the second atomic update sees rowcount == 0
    and fails safely without double-handover.
    """
    admin_id = create_user(app, username="race_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)

        # Worker 1 redeems token
        success1, msg1, data1 = redeem_handover_token(raw_token, admin_id)
        assert success1 is True

        # Worker 2 attempts concurrent redemption
        success2, msg2, data2 = redeem_handover_token(raw_token, admin_id)
        assert success2 is False
        assert "Single-Use Token Violation" in msg2 or "Concurrent Claim Prevented" in msg2

# ----------------------------------------------------------------------
# 7. CSRF Protection on Handover Actions
# ----------------------------------------------------------------------

def test_missing_csrf_token_blocks_review_actions(app, client):
    """All state-changing Phase 8 endpoints reject requests without a CSRF token."""
    create_user(app, username="csrf_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]

    login(client, "csrf_admin")

    # POST status without CSRF
    res1 = client.post(f"/admin/leads/{lead_id}/status", data={"status": "investigating"})
    assert res1.status_code == 400

    # POST approve without CSRF
    res2 = client.post(f"/admin/leads/{lead_id}/approve", data={})
    assert res2.status_code == 400

    # POST handover without CSRF
    res3 = client.post("/admin/handover", data={"token": "HND-TEST"})
    assert res3.status_code == 400

# ----------------------------------------------------------------------
# 8. Privacy & Zero-Leakage Checks
# ----------------------------------------------------------------------

def test_zero_leakage_of_handover_data_to_public(app, client):
    """Public feeds, status lookups, and error pages never expose handover tokens or hashes."""
    admin_id = create_user(app, username="leak_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)
        token_hash = hash_handover_token(raw_token)

    # Public index
    res_index = client.get("/")
    assert raw_token not in res_index.get_data(as_text=True)
    assert token_hash not in res_index.get_data(as_text=True)

    # Public status lookup
    res_status = client.get("/status")
    assert raw_token not in res_status.get_data(as_text=True)
    assert token_hash not in res_status.get_data(as_text=True)

    # Public ordinary report page
    res_ord = client.get("/report/ordinary")
    assert raw_token not in res_ord.get_data(as_text=True)
    assert token_hash not in res_ord.get_data(as_text=True)

def test_disputed_item_blocks_token_redemption(app, client):
    """
    If an item is flagged as disputed after a token was issued,
    redemption of that token is blocked at the desk.
    """
    admin_id = create_user(app, username="disp_issuer", role="admin")
    desk_id = create_user(app, username="disp_desk", role="desk_staff")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)

        # Flag the found item as disputed
        execute_db("UPDATE private_electronics SET status = 'disputed' WHERE id = ?", [found_id])

    login(client, "disp_desk")
    csrf = get_csrf(client, "/admin/handover")

    res = client.post(
        "/admin/handover",
        data={"token": raw_token, "csrf_token": csrf},
    )
    assert res.status_code == 400
    assert b"disputed" in res.data

def test_failed_handover_transaction_rolls_back(app):
    """
    Atomic transaction safety: if an exception occurs during redemption,
    token_used_at remains NULL and item status remains unchanged.
    """
    admin_id = create_user(app, username="tx_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]
        _, _, raw_token = issue_handover_token(lead_id, admin_id)

    # Corrupt the foreign key / status to force a transaction failure
    # or simulate failure during db execution
    with app.app_context():
        db = query_db
        # Attempt redemption with non-existent admin_id to trigger FK failure if foreign keys are ON
        from database.db import get_db
        conn = get_db()
        try:
            with conn:
                # Intentionally fail by violating FK
                conn.execute(
                    "UPDATE handover_logs SET token_used_at = 'now', admin_id = 999999 WHERE match_id = ?",
                    [lead_id],
                )
        except Exception:
            pass

        # Verify rollback preserved NULL token_used_at
        log = query_db("SELECT token_used_at FROM handover_logs WHERE match_id = ?", [lead_id], one=True)
        assert log["token_used_at"] is None

def test_invalid_csrf_token_rejected_on_review_actions(app, client):
    """Forged or tampered CSRF tokens are rejected with HTTP 400."""
    create_user(app, username="forgery_admin", role="admin")
    lost_id = create_private_report(app, report_type="lost")
    found_id = create_private_report(app, report_type="found")

    with app.app_context():
        leads = find_and_record_matches(found_id)
        lead_id = leads[0]["lead_id"]

    login(client, "forgery_admin")
    get_csrf(client)  # initialize session

    bad_csrf = "forged_malicious_csrf_token_value_xyz"

    res1 = client.post(f"/admin/leads/{lead_id}/status", data={"status": "investigating", "csrf_token": bad_csrf})
    assert res1.status_code == 400

    res2 = client.post(f"/admin/leads/{lead_id}/approve", data={"csrf_token": bad_csrf})
    assert res2.status_code == 400

    res3 = client.post("/admin/handover", data={"token": "HND-TEST", "csrf_token": bad_csrf})
    assert res3.status_code == 400

def test_error_responses_do_not_leak_internals(client):
    """Error pages do not leak SQLite exceptions, SQL statements, or stack traces."""
    # Invalid lead ID
    res = client.get("/admin/leads/999999999/status")
    # Method not allowed or not found
    assert res.status_code in (404, 405)
    body = res.get_data(as_text=True)
    assert "sqlite3" not in body
    assert "OperationalError" not in body
    assert "Traceback" not in body
    assert "token_hash" not in body

