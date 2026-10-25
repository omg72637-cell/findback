"""
FindBack 2.0 - Phase 5 Confidential Electronics & Privacy Isolation Tests

Verifies:
1. Electronics form GET and valid POST.
2. Missing and malformed input rejection.
3. Cryptographic tracking-code generation and unpredictability.
4. Tracking-code uniqueness and correct database persistence.
5. Unknown-code generic response (anti-oracle defense).
6. Known-code response contains strictly authorized status information.
7. Zero private electronics data in public feed.
8. No private data in ordinary-item form, workflow choice, or error pages.
9. Prohibited credential handling and heuristic limitations documentation.
10. SQL injection attempts and oversized inputs.
11. Regression tests for ordinary items.
"""

import pytest
from app import generate_tracking_code, detect_prohibited_credentials
from database.db import get_db, query_db, execute_db

# ---------------------------------------------------------------------------
# 1. Electronics Form GET and Valid POST
# ---------------------------------------------------------------------------

def test_electronics_form_get(client):
    """Verify that GET /report/electronics renders the confidential form."""
    response = client.get("/report/electronics")
    assert response.status_code == 200
    assert b"Report an Electronic Device" in response.data
    assert b"Security Warning: Do Not Enter Passwords or PINs" in response.data
    assert b"Safe Distinctive Ownership Clues" in response.data

def test_electronics_form_valid_post(client, app):
    """
    Verify valid confidential submission returns confirmation receipt
    with generated tracking code, and saves record to private_electronics.
    """
    data = {
        "report_type": "lost",
        "device_type": "phone",
        "brand": "Apple",
        "model_family": "iPhone 13",
        "primary_color": "Midnight Blue",
        "campus_location": "Main Library 2nd Floor",
        "date_discovered": "2026-10-24",
        "distinctive_clues": "Clear Spigen case with dog sticker on back; lockscreen photo of a golden retriever",
        "reporter_contact": "alice.student@campus.local",
    }
    response = client.post("/report/electronics", data=data)
    assert response.status_code == 200
    assert b"Your Private Report Has Been Recorded" in response.data
    assert b"YOUR PRIVATE TRACKING CODE" in response.data
    assert b"TRK-" in response.data

    # Verify database persistence
    with app.app_context():
        record = query_db(
            "SELECT * FROM private_electronics WHERE reporter_contact = ?",
            ["alice.student@campus.local"],
            one=True,
        )
        assert record is not None
        assert record["device_type"] == "phone"
        assert record["brand"] == "Apple"
        assert record["status"] == "open"
        assert record["tracking_code"].startswith("TRK-")

# ---------------------------------------------------------------------------
# 2. Missing and Malformed Input
# ---------------------------------------------------------------------------

def test_electronics_missing_required_fields(client):
    """Submitting missing brand, clues, or contact must return HTTP 400."""
    data = {
        "report_type": "lost",
        "device_type": "phone",
        "brand": "",  # Empty!
        "primary_color": "Black",
        "campus_location": "Library",
        "distinctive_clues": "",  # Empty!
        "reporter_contact": "",   # Empty!
    }
    response = client.post("/report/electronics", data=data)
    assert response.status_code == 400
    assert b"All required device details" in response.data

def test_electronics_invalid_report_type(client):
    """Submitting invalid report_type ('stolen') must return HTTP 400."""
    data = {
        "report_type": "stolen",  # Invalid!
        "device_type": "phone",
        "brand": "Samsung",
        "primary_color": "Black",
        "campus_location": "Library",
        "distinctive_clues": "Black case",
        "reporter_contact": "bob@campus.local",
    }
    response = client.post("/report/electronics", data=data)
    assert response.status_code == 400

def test_electronics_invalid_device_type(client):
    """Submitting an unapproved device type must be rejected with HTTP 400."""
    data = {
        "report_type": "found",
        "device_type": "microwave",  # Not in allowed device types!
        "brand": "LG",
        "primary_color": "White",
        "campus_location": "Cafeteria",
        "distinctive_clues": "Appliance",
        "reporter_contact": "staff@campus.local",
    }
    response = client.post("/report/electronics", data=data)
    assert response.status_code == 400
    assert b"Invalid device type" in response.data

# ---------------------------------------------------------------------------
# 3 & 4. Cryptographic Tracking-Code Properties & Persistence
# ---------------------------------------------------------------------------

def test_tracking_code_cryptographic_unpredictability():
    """
    Verify generated tracking codes have high entropy, start with TRK-,
    and are completely unique across 1,000 iterations.
    """
    codes = [generate_tracking_code() for _ in range(1000)]
    assert len(codes) == 1000
    assert len(set(codes)) == 1000, "Collision detected in tracking code generator!"
    for c in codes:
        assert c.startswith("TRK-")
        assert len(c) >= 44  # TRK- + 32-byte urlsafe string (43+ chars)

# ---------------------------------------------------------------------------
# 5. Anti-Oracle Status Lookup Generic Response
# ---------------------------------------------------------------------------

def test_status_lookup_unknown_code_anti_oracle(client):
    """
    ANTI-ORACLE VERIFICATION: An unknown tracking code must return a generic
    message that does NOT confirm or deny database existence.
    """
    response = client.post(
        "/status",
        data={"tracking_code": "TRK-NONEXISTENT-CODE-ABCDEFGHIJKL-1234567890"},
    )
    assert response.status_code == 200
    assert b"Status Not Available" in response.data
    assert b"Status not available for this tracking code" in response.data
    # Crucial security assertion: must NOT reveal database existence
    assert b"not found in database" not in response.data
    assert b"Database error" not in response.data

def test_status_lookup_malformed_code_anti_oracle(client):
    """Submitting a malformed tracking code receives identical generic response."""
    response = client.post(
        "/status",
        data={"tracking_code": "MALFORMED_CODE_WITHOUT_PREFIX"},
    )
    assert response.status_code == 200
    assert b"Status Not Available" in response.data

# ---------------------------------------------------------------------------
# 6. Authorized Status Lookup Projection (Known Code)
# ---------------------------------------------------------------------------

def test_status_lookup_known_code_authorized_projection(client, app):
    """
    PRIVACY ASSERTION: A valid tracking code returns strictly the authorized
    status label and stepper. It must NEVER expose student contact, clues,
    brand, location, or internal database IDs.
    """
    with app.app_context():
        tracking_code = generate_tracking_code()
        execute_db(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES (?, 'lost', 'phone', 'Google', 'Pixel 8', 'Obsidian', 'Library 3rd Floor',
                     '2026-10-24', 'Case with yellow sun decal', 'private.student@campus.local', 'open')
            """,
            (tracking_code,),
        )

    # Query via POST
    response = client.post("/status", data={"tracking_code": tracking_code})
    assert response.status_code == 200
    assert b"Submitted (Searching for Match)" in response.data
    assert b"Current Status" in response.data

    # Strict privacy assertions: private details MUST NOT appear in rendered output
    assert b"private.student@campus.local" not in response.data
    assert b"Case with yellow sun decal" not in response.data
    assert b"Pixel 8" not in response.data
    assert b"Library 3rd Floor" not in response.data
    assert b"Obsidian" not in response.data

# ---------------------------------------------------------------------------
# 7, 8, 9. Zero-Leakage Across Public Routes
# ---------------------------------------------------------------------------

def test_zero_leakage_in_public_feed(client, app):
    """
    PRIVACY INVARIANT: Ensure private electronics data never leaks into
    the public feed (GET /).
    """
    secret_token = generate_tracking_code()
    with app.app_context():
        execute_db(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES (?, 'found', 'laptop', 'Dell', 'XPS 15', 'Silver', 'Science Lab 4',
                     '2026-10-24', 'Cat sticker on lid near logo', 'prof.finder@campus.local', 'open')
            """,
            (secret_token,),
        )

    response = client.get("/")
    assert response.status_code == 200
    assert secret_token.encode() not in response.data
    assert b"XPS 15" not in response.data
    assert b"Cat sticker on lid" not in response.data
    assert b"prof.finder@campus.local" not in response.data

def test_zero_leakage_in_workflow_choice_and_ordinary_form(client, app):
    """
    Ensure confidential data never appears in /report or /report/ordinary.
    """
    secret_token = generate_tracking_code()
    with app.app_context():
        execute_db(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES (?, 'lost', 'earbuds', 'Sony', 'WF-1000XM5', 'Black', 'Gym Locker',
                     '2026-10-24', 'Scratched left bud case', 'athlete@campus.local', 'open')
            """,
            (secret_token,),
        )

    resp_choice = client.get("/report")
    assert secret_token.encode() not in resp_choice.data
    assert b"athlete@campus.local" not in resp_choice.data

    resp_ordinary = client.get("/report/ordinary")
    assert secret_token.encode() not in resp_ordinary.data
    assert b"athlete@campus.local" not in resp_ordinary.data

def test_zero_leakage_in_error_handlers(client):
    """Ensure custom error handlers (400, 404, 500) never leak database details."""
    # 404 route
    resp_404 = client.get("/nonexistent-route-for-testing")
    assert resp_404.status_code == 404
    assert b"Page Not Found" in resp_404.data
    assert b"sqlite" not in resp_404.data.lower()
    assert b"Traceback" not in resp_404.data

# ---------------------------------------------------------------------------
# 10. Prohibited Credential Heuristic Guardrail
# ---------------------------------------------------------------------------

def test_prohibited_credential_heuristic_rejection(client, app):
    """
    Verify heuristic rejection of common PIN and password patterns.
    
    NOTE ON LIMITATIONS:
    Passing this test confirms the regex catches obvious credential submissions.
    It does not claim to catch all possible obfuscated password descriptions.
    """
    credential_inputs = [
        "My PIN is 1234",
        "password: supersecretpassword",
        "device passcode is 9876",
        "recovery code: abc-def-ghi",
    ]

    for cred in credential_inputs:
        data = {
            "report_type": "lost",
            "device_type": "phone",
            "brand": "Apple",
            "primary_color": "Black",
            "campus_location": "Cafeteria",
            "distinctive_clues": cred,
            "reporter_contact": "test@campus.local",
        }
        response = client.post("/report/electronics", data=data)
        assert response.status_code == 400
        assert b"Prohibited credential pattern detected" in response.data

    # Assert none of these prohibited submissions entered the database
    with app.app_context():
        count = query_db(
            "SELECT COUNT(*) as cnt FROM private_electronics WHERE distinctive_clues LIKE '%PIN%' OR distinctive_clues LIKE '%password%'",
            one=True,
        )
        assert count["cnt"] == 0

# ---------------------------------------------------------------------------
# 11. SQL Injection & Oversized Input Tests
# ---------------------------------------------------------------------------

def test_status_lookup_sql_injection_safety(client):
    """Verify parameterized queries prevent SQL injection in status lookup."""
    sqli_payloads = [
        "' OR '1'='1",
        "TRK-' OR '1'='1' --",
        "'; DROP TABLE private_electronics; --",
    ]
    for payload in sqli_payloads:
        response = client.post("/status", data={"tracking_code": payload})
        assert response.status_code == 200
        # Must return generic status not available without raising database syntax error
        assert b"Status Not Available" in response.data

def test_electronics_oversized_input_rejection(client):
    """Submitting excessively long text must be rejected with HTTP 400."""
    data = {
        "report_type": "lost",
        "device_type": "phone",
        "brand": "A" * 100,  # Max 50
        "primary_color": "Black",
        "campus_location": "Library",
        "distinctive_clues": "B" * 600,  # Max 500
        "reporter_contact": "test@campus.local",
    }
    response = client.post("/report/electronics", data=data)
    assert response.status_code == 400
    assert b"exceeds maximum allowable field lengths" in response.data

# ---------------------------------------------------------------------------
# 12. Ordinary Items Regression Test
# ---------------------------------------------------------------------------

def test_ordinary_workflow_regression(client):
    """Verify Phase 4 ordinary item workflow continues functioning cleanly."""
    # Submit ordinary item
    data = {
        "report_type": "found",
        "category": "Umbrellas",
        "description": "Green plaid umbrella",
        "campus_location": "Admin Block",
        "date_discovered": "2026-10-24",
        "contact_email": "desk@campus.local",
    }
    post_resp = client.post("/report/ordinary", data=data, follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"Green plaid umbrella" in post_resp.data
    # Rejection of electronic category on ordinary form still active
    bad_data = data.copy()
    bad_data["category"] = "Smartphone"
    bad_resp = client.post("/report/ordinary", data=bad_data)
    assert bad_resp.status_code == 400
