"""
FindBack 2.0 - Public Route & Allowlist Integration Tests (Phase 4)
"""

from database.db import get_db, init_db_schema, execute_db

def test_public_feed_get_ok(client, app):
    """Verify that GET / returns HTTP 200 and renders the public feed."""
    with app.app_context():
        init_db_schema()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Find What Was Lost" in response.data
    assert b"Ordinary Everyday Items" in response.data

def test_report_ordinary_get_ok(client, app):
    """Verify that GET /report/ordinary renders the ordinary submission form."""
    with app.app_context():
        init_db_schema()
    response = client.get("/report/ordinary")
    assert response.status_code == 200
    assert b"Report an Ordinary Item" in response.data
    assert b"Water Bottles &amp; Mugs" in response.data or b"Water Bottles" in response.data

def test_report_ordinary_valid_submission(client, app):
    """Verify valid ordinary submission redirects to / and persists record."""
    with app.app_context():
        init_db_schema()
    data = {
        "report_type": "found",
        "category": "Water Bottles & Mugs",
        "description": "Green insulated metal flask",
        "campus_location": "Main Library Table 4",
        "date_discovered": "2026-10-24",
        "contact_email": "student1@campus.local",
    }
    response = client.post("/report/ordinary", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Green insulated metal flask" in response.data
    assert b"Ordinary item report successfully published" in response.data

def test_report_ordinary_rejects_electronic_category(client, app):
    """
    CRITICAL SECURITY CHECK: Submitting an electronic category (Smartphone)
    to the ordinary form MUST be rejected with HTTP 400.
    """
    with app.app_context():
        init_db_schema()
    data = {
        "report_type": "found",
        "category": "Smartphone",  # Prohibited on public board!
        "description": "Black iPhone 13 found in corridor",
        "campus_location": "Main Hall",
        "date_discovered": "2026-10-24",
        "contact_email": "student2@campus.local",
    }
    response = client.post("/report/ordinary", data=data)
    assert response.status_code == 400
    assert b"not on the approved ordinary allowlist" in response.data

def test_report_ordinary_rejects_empty_category(client, app):
    """Submitting with empty category must be rejected with HTTP 400."""
    with app.app_context():
        init_db_schema()
    data = {
        "report_type": "found",
        "category": "",
        "description": "Lost blue umbrella",
        "campus_location": "Science Block",
        "date_discovered": "2026-10-24",
        "contact_email": "student3@campus.local",
    }
    response = client.post("/report/ordinary", data=data)
    assert response.status_code == 400

def test_public_feed_does_not_expose_contact_email(client, app):
    """
    PRIVACY ASSERTION: The contact_email must never be rendered on the
    public listings feed, even if it is stored in ordinary_items.
    """
    with app.app_context():
        init_db_schema()
        execute_db(
            """
            INSERT INTO ordinary_items (
                report_type, category, description, campus_location,
                date_discovered, status, contact_email
            ) VALUES (?, ?, ?, ?, ?, 'available', ?)
            """,
            (
                "found",
                "Umbrellas",
                "Unique yellow umbrella with cat pattern",
                "Cafeteria",
                "2026-10-24",
                "secret.student@campus.local",
            ),
        )

    response = client.get("/")
    assert response.status_code == 200
    assert b"Unique yellow umbrella with cat pattern" in response.data
    # Structured assertion: contact email must NOT be in the rendered response
    assert b"secret.student@campus.local" not in response.data

def test_public_feed_zero_leakage_of_private_electronics(client, app):
    """
    PRIVACY ASSERTION: Zero private electronics data or tracking codes
    may appear in the public feed response under any circumstance.
    """
    with app.app_context():
        init_db_schema()
        execute_db(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """,
            (
                "TRK-SECRET-CODE-9999",
                "lost",
                "phone",
                "Apple",
                "iPhone 14 Pro",
                "Space Black",
                "CS Lab 101",
                "2026-10-24",
                "Lockscreen has picture of orange cat; blue case",
                "victim@campus.local",
            ),
        )

    response = client.get("/")
    assert response.status_code == 200
    assert b"TRK-SECRET-CODE-9999" not in response.data
    assert b"iPhone 14 Pro" not in response.data
    assert b"picture of orange cat" not in response.data
    assert b"victim@campus.local" not in response.data
    assert b"distinctive_clues" not in response.data
    assert b"reporter_contact" not in response.data
