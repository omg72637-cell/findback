"""
FindBack 2.0 - Database Constraint and Security Unit Tests (Phase 3)
"""

import sqlite3
import pytest
from werkzeug.security import check_password_hash
from database.db import get_db, init_db_schema, query_db, execute_db
from database.init_db import init_database

def test_schema_creation_and_tables(app):
    """Verify that all five tables exist in the initialized schema."""
    with app.app_context():
        db = get_db()
        init_db_schema(db)
        tables = query_db(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        table_names = [t["name"] for t in tables]
        expected = [
            "admin_users",
            "handover_logs",
            "match_leads",
            "ordinary_items",
            "private_electronics",
        ]
        for exp in expected:
            assert exp in table_names

def test_ordinary_items_allowlist_constraint(app):
    """
    Verify CHECK constraint: inserting a high-value electronic category
    into ordinary_items MUST raise sqlite3.IntegrityError.
    """
    with app.app_context():
        db = get_db()
        init_db_schema(db)
        
        with pytest.raises(sqlite3.IntegrityError):
            execute_db(
                """
                INSERT INTO ordinary_items (
                    report_type, category, description, campus_location,
                    date_discovered, contact_email
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "found",
                    "Smartphone",  # NOT on ordinary allowlist!
                    "iPhone found in library",
                    "Library",
                    "2026-10-24",
                    "staff@campus.local",
                ),
            )

def test_report_type_constraint(app):
    """Verify CHECK constraint: report_type must be either 'lost' or 'found'."""
    with app.app_context():
        db = get_db()
        init_db_schema(db)
        
        with pytest.raises(sqlite3.IntegrityError):
            execute_db(
                """
                INSERT INTO ordinary_items (
                    report_type, category, description, campus_location,
                    date_discovered, contact_email
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "stolen",  # Invalid report_type!
                    "Umbrellas",
                    "Black umbrella",
                    "Science Block",
                    "2026-10-24",
                    "staff@campus.local",
                ),
            )

def test_foreign_key_enforcement(app):
    """
    Verify foreign keys: inserting a match_lead referencing a non-existent
    electronics report ID must fail with IntegrityError.
    """
    with app.app_context():
        db = get_db()
        init_db_schema(db)
        
        with pytest.raises(sqlite3.IntegrityError):
            execute_db(
                """
                INSERT INTO match_leads (
                    lost_report_id, found_report_id, match_score,
                    score_breakdown_json
                ) VALUES (?, ?, ?, ?)
                """,
                (9999, 8888, 85, '{"breakdown": "test"}'),
            )

def test_parameterized_query_safety(app):
    """Verify parameterized queries handle SQL injection attempts safely."""
    with app.app_context():
        db = get_db()
        init_db_schema(db)
        
        # Insert a valid ordinary item
        execute_db(
            """
            INSERT INTO ordinary_items (
                report_type, category, description, campus_location,
                date_discovered, contact_email
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "found",
                "Umbrellas",
                "Blue umbrella",
                "Library",
                "2026-10-24",
                "staff@campus.local",
            ),
        )
        
        # Attempt classic SQL injection payload in parameter
        sqli_payload = "' OR '1'='1"
        results = query_db(
            "SELECT * FROM ordinary_items WHERE description = ?",
            [sqli_payload],
        )
        # Should return 0 records because parameter is treated literally
        assert len(results) == 0


def test_init_db_missing_admin_password_raises_error(tmp_path, monkeypatch):
    """
    Verify that initializing a new database without INITIAL_ADMIN_PASSWORD
    raises a clear ValueError and does not create an insecure default account.
    """
    test_db_path = tmp_path / "missing_admin.db"
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("INITIAL_DESK_STAFF_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="INITIAL_ADMIN_PASSWORD") as exc_info:
        init_database(db_path=test_db_path, load_env=False)

    assert "INITIAL_ADMIN_PASSWORD" in str(exc_info.value)
    assert "admin" in str(exc_info.value)


def test_init_db_missing_desk_staff_password_raises_error(tmp_path, monkeypatch):
    """
    Verify that initializing a new database with admin password set but
    missing INITIAL_DESK_STAFF_PASSWORD raises a clear ValueError.
    """
    test_db_path = tmp_path / "missing_desk.db"
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "AdminSecretPass123!")
    monkeypatch.delenv("INITIAL_DESK_STAFF_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="INITIAL_DESK_STAFF_PASSWORD") as exc_info:
        init_database(db_path=test_db_path, load_env=False)

    assert "INITIAL_DESK_STAFF_PASSWORD" in str(exc_info.value)
    assert "desk_staff" in str(exc_info.value)


def test_init_db_success_with_environment_passwords(tmp_path, monkeypatch):
    """
    Verify that providing valid environment passwords initializes tables,
    hashes passwords correctly, and populates staff roles on an isolated database.
    """
    test_db_path = tmp_path / "seeded_success.db"
    admin_pw = "CustomAdminPass789!"
    desk_pw = "CustomDeskPass456!"
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", admin_pw)
    monkeypatch.setenv("INITIAL_DESK_STAFF_PASSWORD", desk_pw)

    init_database(db_path=test_db_path, load_env=False)

    # Verify tables and records in the isolated database
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin_users WHERE username = ?", ["admin"])
        admin_row = cur.fetchone()
        assert admin_row is not None
        assert admin_row["role"] == "admin"
        assert admin_row["is_active"] == 1
        assert check_password_hash(admin_row["password_hash"], admin_pw)
        # Ensure raw password was never stored
        assert admin_row["password_hash"] != admin_pw

        cur.execute("SELECT * FROM admin_users WHERE username = ?", ["desk_staff"])
        desk_row = cur.fetchone()
        assert desk_row is not None
        assert desk_row["role"] == "desk_staff"
        assert desk_row["is_active"] == 1
        assert check_password_hash(desk_row["password_hash"], desk_pw)
        assert desk_row["password_hash"] != desk_pw

        # Ensure ordinary items were seeded
        cur.execute("SELECT COUNT(*) as count FROM ordinary_items")
        assert cur.fetchone()["count"] == 4
    finally:
        conn.close()


def test_init_db_preserves_existing_accounts_without_overwriting(tmp_path, monkeypatch):
    """
    Verify that re-running init_database on an existing database preserves
    existing accounts and hashes, even if INITIAL_*_PASSWORD env vars are unset.
    """
    test_db_path = tmp_path / "idempotent.db"
    original_admin_pw = "OriginalAdminPw111!"
    original_desk_pw = "OriginalDeskPw222!"
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", original_admin_pw)
    monkeypatch.setenv("INITIAL_DESK_STAFF_PASSWORD", original_desk_pw)

    # First initialization
    init_database(db_path=test_db_path, load_env=False)

    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM admin_users WHERE username = 'admin'")
        initial_admin_hash = cur.fetchone()["password_hash"]
        cur.execute("SELECT password_hash FROM admin_users WHERE username = 'desk_staff'")
        initial_desk_hash = cur.fetchone()["password_hash"]
    finally:
        conn.close()

    # Now remove environment variables completely
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("INITIAL_DESK_STAFF_PASSWORD", raising=False)

    # Re-run init_database: should NOT raise ValueError, and should NOT overwrite hashes
    init_database(db_path=test_db_path, load_env=False)

    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM admin_users WHERE username = 'admin'")
        assert cur.fetchone()["password_hash"] == initial_admin_hash

        cur.execute("SELECT password_hash FROM admin_users WHERE username = 'desk_staff'")
        assert cur.fetchone()["password_hash"] == initial_desk_hash
    finally:
        conn.close()
