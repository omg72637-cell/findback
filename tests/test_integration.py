"""
FindBack 2.0 - Comprehensive End-to-End Integration & Usability Tests (Phase 9)

Tests the complete lifecycle of ordinary and confidential reporting workflows,
deterministic matching, tiered RBAC, dispute freezing, single-use token handover,
anti-oracle projection, and accessibility compliance.
All test data is purely synthetic.
"""

import json
import re
from werkzeug.security import generate_password_hash
from database.db import query_db, execute_db
from matching.service import hash_handover_token

def _extract_csrf_token(html_bytes: bytes) -> str:
    """Helper to extract session-bound CSRF token from rendered HTML."""
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_bytes.decode("utf-8"))
    if not match:
        raise ValueError("CSRF token not found in response HTML.")
    return match.group(1)

def _extract_tracking_code(html_bytes: bytes) -> str:
    """Helper to extract TRK-... code from confirmation receipt HTML."""
    match = re.search(r'TRK-[A-Za-z0-9_-]+', html_bytes.decode("utf-8"))
    if not match:
        raise ValueError("Tracking code not found in response HTML.")
    return match.group(0)

def _extract_handover_token(html_bytes: bytes) -> str:
    """Helper to extract HND-... token from token issued receipt HTML."""
    match = re.search(r'HND-[A-Za-z0-9_-]+', html_bytes.decode("utf-8"))
    if not match:
        raise ValueError("Handover token not found in response HTML.")
    return match.group(0)


# ---------------------------------------------------------------------------
# 1. Full Ordinary Items Workflow (Workflow A End-to-End)
# ---------------------------------------------------------------------------

def test_e2e_ordinary_workflow(client):
    """
    Test complete Ordinary Items user journey:
    1. Submit valid ordinary item.
    2. Redirects to public feed with success message.
    3. Item appears on feed with search and category filtering.
    4. Private contact email is never exposed in the public feed HTML.
    5. Submitting an electronic category is strictly rejected with HTTP 400.
    """
    # 1. Submit valid ordinary item
    data = {
        "report_type": "found",
        "category": "Water Bottles & Mugs",
        "description": "Synthetic blue stainless insulated flask with mountain sticker",
        "campus_location": "Science Block 2nd Floor Lounge",
        "date_discovered": "2026-10-24",
        "contact_email": "desk.finder@campus.local",
    }
    res = client.post("/report/ordinary", data=data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Ordinary item report successfully published" in res.data
    assert b"Synthetic blue stainless insulated flask" in res.data

    # 2. Search filtering
    search_res = client.get("/?q=mountain")
    assert search_res.status_code == 200
    assert b"Synthetic blue stainless insulated flask" in search_res.data

    miss_res = client.get("/?q=nonexistent_xyz")
    assert miss_res.status_code == 200
    assert b"No ordinary items found" in miss_res.data

    # 3. Category filtering
    cat_res = client.get("/?category=Water+Bottles+%26+Mugs")
    assert cat_res.status_code == 200
    assert b"Synthetic blue stainless insulated flask" in cat_res.data

    other_cat_res = client.get("/?category=Umbrellas")
    assert other_cat_res.status_code == 200
    assert b"No ordinary items found" in other_cat_res.data

    # 4. Strict privacy assertion: contact email NEVER appears in public feed
    assert b"desk.finder@campus.local" not in res.data
    assert b"desk.finder@campus.local" not in search_res.data
    assert b"desk.finder@campus.local" not in cat_res.data

    # 5. Allowlist violation: submitting smartphone to ordinary form
    bad_data = {
        "report_type": "found",
        "category": "Smartphone",
        "description": "Found phone",
        "campus_location": "Cafeteria",
        "date_discovered": "2026-10-24",
        "contact_email": "student@campus.local",
    }
    bad_res = client.post("/report/ordinary", data=bad_data)
    assert bad_res.status_code == 400
    assert b"not on the approved ordinary allowlist" in bad_res.data


# ---------------------------------------------------------------------------
# 2. Full Confidential Electronics Lifecycle (Workflow B End-to-End)
# ---------------------------------------------------------------------------

def test_e2e_confidential_electronics_matching_approval_handover_lifecycle(client, app):
    """
    Test complete Confidential Electronics journey end-to-end:
    1. Student reports lost phone -> receives tracking code A -> status 'open'.
    2. Finder reports found phone -> receives tracking code B.
    3. Deterministic matching runs automatically -> lead created -> status 'lead_identified'.
    4. Desk staff attempts to approve lead -> rejected with HTTP 403 Forbidden.
    5. Admin reviews lead, inspects clue breakdown, and approves lead -> raw single-use token issued.
    6. Tracking code A status transitions to 'ready_for_handover' (Step 4).
    7. Desk staff redeems token at custody desk -> items marked 'resolved' (Step 5).
    8. Single-use token replay attempt rejected with HTTP 400.
    """
    with app.app_context():
        # Seed admin and desk_staff accounts
        execute_db(
            """
            INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 1), (?, ?, ?, ?, 1)
            """,
            (
                "super_admin",
                generate_password_hash("AdminPass123!"),
                "Campus Admin",
                "admin",
                "front_desk",
                generate_password_hash("DeskPass123!"),
                "Desk Officer",
                "desk_staff",
            ),
        )

    # Step 1: Student A submits confidential lost phone
    lost_data = {
        "report_type": "lost",
        "device_type": "phone",
        "brand": "Apple",
        "model_family": "iPhone 13",
        "primary_color": "Midnight Blue",
        "campus_location": "Library 2nd Floor Study Cubicle",
        "date_discovered": "2026-10-24",
        "distinctive_clues": "Matte clear case with small holographic owl sticker",
        "reporter_contact": "student_lost@campus.local",
    }
    lost_res = client.post("/report/electronics", data=lost_data)
    assert lost_res.status_code == 200
    assert b"Your Private Report Has Been Recorded" in lost_res.data
    trk_lost = _extract_tracking_code(lost_res.data)

    # Status check for lost report: Submitted (Searching for Match)
    st1 = client.post("/status", data={"tracking_code": trk_lost})
    assert st1.status_code == 200
    assert b"Submitted (Searching for Match)" in st1.data

    # Step 2: Finder submits matching found phone
    found_data = {
        "report_type": "found",
        "device_type": "phone",
        "brand": "Apple",
        "model_family": "iPhone 13",
        "primary_color": "Midnight Blue",
        "campus_location": "Library 2nd Floor Reading Room",
        "date_discovered": "2026-10-24",
        "distinctive_clues": "Clear case with small owl decal on lower right",
        "reporter_contact": "finder@campus.local",
    }
    found_res = client.post("/report/electronics", data=found_data)
    assert found_res.status_code == 200
    trk_found = _extract_tracking_code(found_res.data)

    # Lead should have been generated automatically!
    with app.app_context():
        leads = query_db("SELECT * FROM match_leads")
        assert len(leads) == 1
        lead = leads[0]
        assert lead["match_score"] >= 80
        assert lead["review_status"] == "pending_review"

    # Status check for lost report: Under Staff Review (Step 3)
    st2 = client.post("/status", data={"tracking_code": trk_lost})
    assert st2.status_code == 200
    assert b"Under Staff Review" in st2.data

    # Step 3: Tiered RBAC - Desk staff tries to approve lead -> must receive HTTP 403
    # Login as desk_staff
    login_get = client.get("/admin/login")
    login_csrf = _extract_csrf_token(login_get.data)
    client.post("/admin/login", data={"username": "front_desk", "password": "DeskPass123!", "csrf_token": login_csrf})

    # Desk staff views leads queue (allowed)
    desk_queue = client.get("/admin/leads")
    assert desk_queue.status_code == 200
    assert b"Queue view only" in desk_queue.data
    desk_auth_csrf = _extract_csrf_token(desk_queue.data)

    # Desk staff attempts to approve lead (forbidden)
    desk_approve = client.post(f"/admin/leads/{lead['id']}/approve", data={"csrf_token": desk_auth_csrf})
    assert desk_approve.status_code == 403

    # Desk staff logout
    client.post("/admin/logout", data={"csrf_token": desk_auth_csrf})

    # Step 4: Admin logs in and approves lead
    login_get2 = client.get("/admin/login")
    login_csrf2 = _extract_csrf_token(login_get2.data)
    client.post("/admin/login", data={"username": "super_admin", "password": "AdminPass123!", "csrf_token": login_csrf2})

    # Admin visits review queue and clicks approve
    admin_queue = client.get("/admin/leads")
    assert admin_queue.status_code == 200
    assert b"Approve &amp; Issue Token" in admin_queue.data
    assert b"Deterministic Scoring Breakdown:" in admin_queue.data
    admin_auth_csrf = _extract_csrf_token(admin_queue.data)

    approve_res = client.post(f"/admin/leads/{lead['id']}/approve", data={"csrf_token": admin_auth_csrf})
    assert approve_res.status_code == 200
    assert b"Handover Authorization Token" in approve_res.data
    raw_token = _extract_handover_token(approve_res.data)
    assert raw_token.startswith("HND-")

    # Verify token storage: strictly SHA-256 hash in database
    with app.app_context():
        token_log = query_db("SELECT * FROM handover_logs WHERE match_id = ?", [lead["id"]], one=True)
        assert token_log is not None
        assert token_log["token_hash"] == hash_handover_token(raw_token)
        # Raw token must NOT exist in the database table
        assert token_log["token_hash"] != raw_token

    # Step 5: Student A checks status -> Transitions to 'Ready for Desk Handover' (Step 4)
    st3 = client.post("/status", data={"tracking_code": trk_lost})
    assert st3.status_code == 200
    assert b"Ready for Desk Handover" in st3.data
    assert b"Desk staff have verified this lead" in st3.data

    # Step 6: Handover Custody Desk Redemption
    # Officer visits handover desk and redeems token
    handover_page = client.get("/admin/handover")
    desk_csrf2 = _extract_csrf_token(handover_page.data)

    redeem_res = client.post(
        "/admin/handover",
        data={
            "token": raw_token,
            "resolution_notes": "Student ID verified. Claimant unlocked device and confirmed owl sticker.",
            "csrf_token": desk_csrf2,
        },
    )
    assert redeem_res.status_code == 200
    assert b"Handover successfully completed and recorded in custody audit logs" in redeem_res.data
    assert b"Student ID verified" in redeem_res.data

    # Step 7: Verify final resolved states
    with app.app_context():
        lost_db = query_db("SELECT status FROM private_electronics WHERE tracking_code = ?", [trk_lost], one=True)
        found_db = query_db("SELECT status FROM private_electronics WHERE tracking_code = ?", [trk_found], one=True)
        assert lost_db["status"] == "resolved"
        assert found_db["status"] == "resolved"

    st4 = client.post("/status", data={"tracking_code": trk_lost})
    assert st4.status_code == 200
    assert b"Case Resolved" in st4.data
    assert b"This item has been safely returned" in st4.data

    # Step 8: Replay attack prevention: attempting to redeem the same token again fails
    replay_res = client.post(
        "/admin/handover",
        data={"token": raw_token, "csrf_token": desk_csrf2},
    )
    assert replay_res.status_code == 400
    assert b"Single-Use Token Violation" in replay_res.data


# ---------------------------------------------------------------------------
# 3. Full Competing Claim Dispute & Adjudication Journey
# ---------------------------------------------------------------------------

def test_e2e_dispute_competing_claim_freeze_and_adjudication(client, app):
    """
    Test dispute lifecycle end-to-end:
    1. Lost report #1 submitted.
    2. Found report submitted -> creates match lead #1.
    3. Lost report #2 submitted with identical traits -> competing claim detected!
    4. Both match leads flagged 'disputed'; items flagged 'disputed'.
    5. Handover token issuance is blocked by can_lead_proceed_to_handover.
    6. Admin visits disputes view, evaluates competing clues, and dismisses claimant #2.
    7. Dismissal cleanly unfreezes lead #1 from 'disputed' to 'investigating'.
    8. Lead #1 can now be approved and processed through handover.
    """
    with app.app_context():
        execute_db(
            """
            INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
            VALUES ('dispute_admin', ?, 'Dispute Officer', 'admin', 1)
            """,
            (generate_password_hash("Pass12345!"),),
        )

    # 1. Lost report 1 (Claimant 1)
    rep1 = client.post(
        "/report/electronics",
        data={
            "report_type": "lost",
            "device_type": "laptop",
            "brand": "Lenovo",
            "model_family": "ThinkPad T14",
            "primary_color": "Black",
            "campus_location": "CS Department Lab 301",
            "date_discovered": "2026-10-24",
            "distinctive_clues": "Has Linux penguin sticker on corner and red trackpoint cap",
            "reporter_contact": "claimant1@campus.local",
        },
    )
    trk1 = _extract_tracking_code(rep1.data)

    # 2. Found report (Desk Custody)
    rep_found = client.post(
        "/report/electronics",
        data={
            "report_type": "found",
            "device_type": "laptop",
            "brand": "Lenovo",
            "model_family": "ThinkPad T14",
            "primary_color": "Black",
            "campus_location": "CS Lab 301",
            "date_discovered": "2026-10-24",
            "distinctive_clues": "Black laptop with sticker on lid",
            "reporter_contact": "lab_attendant@campus.local",
        },
    )

    # 3. Lost report 2 (Claimant 2, competing)
    rep2 = client.post(
        "/report/electronics",
        data={
            "report_type": "lost",
            "device_type": "laptop",
            "brand": "Lenovo",
            "model_family": "ThinkPad T14",
            "primary_color": "Black",
            "campus_location": "CS Lab 301",
            "date_discovered": "2026-10-24",
            "distinctive_clues": "ThinkPad with CS department asset tag",
            "reporter_contact": "claimant2@campus.local",
        },
    )
    trk2 = _extract_tracking_code(rep2.data)

    # 4. Verify dispute freeze
    with app.app_context():
        leads = query_db("SELECT id, review_status FROM match_leads ORDER BY id")
        assert len(leads) == 2
        assert leads[0]["review_status"] == "disputed"
        assert leads[1]["review_status"] == "disputed"
        lead1_id = leads[0]["id"]
        lead2_id = leads[1]["id"]

    # Status check confirms dispute notice
    st_disp = client.post("/status", data={"tracking_code": trk1})
    assert st_disp.status_code == 200
    assert b"Under Staff Review (Competing Claim)" in st_disp.data
    assert b"Automated progression is frozen" in st_disp.data

    # 5. Admin login
    l_page = client.get("/admin/login")
    login_csrf = _extract_csrf_token(l_page.data)
    client.post("/admin/login", data={"username": "dispute_admin", "password": "Pass12345!", "csrf_token": login_csrf})

    admin_leads_page = client.get("/admin/leads")
    auth_csrf = _extract_csrf_token(admin_leads_page.data)

    # Handover token generation must be blocked while disputed
    block_res = client.post(f"/admin/leads/{lead1_id}/approve", data={"csrf_token": auth_csrf})
    assert block_res.status_code == 400
    assert b"competing claims" in block_res.data

    # 6. Admin visits disputes queue
    disp_page = client.get("/admin/disputes")
    assert disp_page.status_code == 200
    assert b"Competing Candidate Claims" in disp_page.data

    # 7. Admin dismisses claimant 2
    dismiss_res = client.post(
        f"/admin/leads/{lead2_id}/status",
        data={
            "status": "dismissed",
            "notes": "Adjudication: Claimant 2 asset tag did not match custody laptop traits.",
            "csrf_token": auth_csrf,
        },
        follow_redirects=True,
    )
    assert dismiss_res.status_code == 200

    # 8. Verify lead 1 was cleanly unfrozen
    with app.app_context():
        lead1_after = query_db("SELECT review_status FROM match_leads WHERE id = ?", [lead1_id], one=True)
        lead2_after = query_db("SELECT review_status FROM match_leads WHERE id = ?", [lead2_id], one=True)
        assert lead2_after["review_status"] == "dismissed"
        assert lead1_after["review_status"] == "investigating"

    # Now approval succeeds!
    appr_res = client.post(f"/admin/leads/{lead1_id}/approve", data={"csrf_token": auth_csrf})
    assert appr_res.status_code == 200
    assert b"Handover Authorization Token" in appr_res.data


# ---------------------------------------------------------------------------
# 4. Anti-Oracle and Credential Guardrail End-to-End
# ---------------------------------------------------------------------------

def test_anti_oracle_and_credential_defense_end_to_end(client):
    """
    Test anti-oracle defenses and credential filtering:
    1. Submitting nonexistent code returns generic HTTP 200 without leaking database state.
    2. Submitting text with 'pin' or 'password' is rejected with HTTP 400 security warning.
    """
    # 1. Anti-oracle check
    res = client.post("/status", data={"tracking_code": "TRK-NONEXISTENT-CODE-RANDOM-CHARS-12345"})
    assert res.status_code == 200
    assert b"Status Not Available" in res.data
    assert b"not found in database" not in res.data

    # 2. Heuristic PIN / Password detection
    bad_report = {
        "report_type": "lost",
        "device_type": "phone",
        "brand": "OnePlus",
        "primary_color": "Black",
        "campus_location": "Hostel 4 Ground Floor",
        "date_discovered": "2026-10-24",
        "distinctive_clues": "Device passcode is 9876. Please check notes app.",
        "reporter_contact": "student@campus.local",
    }
    pin_res = client.post("/report/electronics", data=bad_report)
    assert pin_res.status_code == 400
    assert b"Prohibited credential pattern detected" in pin_res.data
    assert b"never enter device unlock PINs, passwords" in pin_res.data


# ---------------------------------------------------------------------------
# 5. Accessibility, Navigation and Mobile Structural Compliance
# ---------------------------------------------------------------------------

def test_accessibility_and_ui_structure(client):
    """
    Verify WCAG accessibility requirements:
    1. 'Skip to main content' link is present on public and staff pages.
    2. Target element <main id="main-content"> exists.
    3. Viewport meta tag is present for mobile responsiveness.
    4. Form inputs have associated accessible label tags.
    """
    routes_to_check = ["/", "/report", "/report/ordinary", "/report/electronics", "/status", "/admin/login"]
    for route in routes_to_check:
        res = client.get(route)
        assert res.status_code == 200
        html = res.data.decode("utf-8")
        assert 'class="skip-link"' in html, f"Skip link missing on {route}"
        assert 'id="main-content"' in html, f"Main content id missing on {route}"
        assert '<meta name="viewport"' in html, f"Viewport meta tag missing on {route}"

    # Verify form inputs in electronics form have matching label 'for' attributes
    elec_res = client.get("/report/electronics")
    elec_html = elec_res.data.decode("utf-8")
    for field_id in ["device_type", "brand", "model_family", "primary_color", "campus_location", "distinctive_clues", "reporter_contact"]:
        assert f'id="{field_id}"' in elec_html
        assert f'for="{field_id}"' in elec_html
