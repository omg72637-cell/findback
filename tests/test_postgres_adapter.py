"""
FindBack 2.0 - PostgreSQL Adapter and Production Health Check Unit Tests
"""

import pytest
from unittest.mock import MagicMock
from database.db import (
    is_postgres_uri,
    adapt_query_for_postgres,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    get_db,
)


def test_is_postgres_uri():
    """Verify detection of PostgreSQL vs SQLite database URIs."""
    assert is_postgres_uri("postgresql://user:pass@ep-cool.neon.tech/neondb?sslmode=require") is True
    assert is_postgres_uri("postgres://user:pass@ep-cool.neon.tech/neondb") is True
    assert is_postgres_uri("findback.db") is False
    assert is_postgres_uri(":memory:") is False
    assert is_postgres_uri("sqlite:///test.db") is False
    assert is_postgres_uri("") is False
    assert is_postgres_uri(None) is False


def test_adapt_query_for_postgres():
    """Verify translation of '?' parameter placeholders to '%s' for PostgreSQL."""
    query = "SELECT id, full_name FROM admin_users WHERE username = ? AND is_active = ?"
    adapted = adapt_query_for_postgres(query)
    assert adapted == "SELECT id, full_name FROM admin_users WHERE username = %s AND is_active = %s"


def test_postgres_cursor_wrapper_query_execution():
    """Verify that PostgresCursorWrapper adapts placeholders and forwards to underlying cursor."""
    mock_raw_cursor = MagicMock()
    mock_raw_cursor.fetchone.return_value = {"id": 1, "username": "admin"}

    wrapper = PostgresCursorWrapper(mock_raw_cursor)
    res = wrapper.execute("SELECT * FROM admin_users WHERE id = ?", [1])

    # Check that '?' was adapted to '%s'
    mock_raw_cursor.execute.assert_called_once_with(
        "SELECT * FROM admin_users WHERE id = %s", [1]
    )
    assert res.fetchone() == {"id": 1, "username": "admin"}


def test_postgres_cursor_wrapper_insert_returning_id():
    """
    Verify that PostgresCursorWrapper automatically appends 'RETURNING id;'
    to INSERT statements and captures the returned ID into 'lastrowid'.
    """
    mock_raw_cursor = MagicMock()
    # Mock returning row [42]
    mock_raw_cursor.fetchone.return_value = (42,)

    wrapper = PostgresCursorWrapper(mock_raw_cursor)
    wrapper.execute(
        "INSERT INTO private_electronics (brand, model_family) VALUES (?, ?)",
        ["Apple", "iPhone 13"],
    )

    # Ensure RETURNING id was appended
    expected_sql = (
        "INSERT INTO private_electronics (brand, model_family) VALUES (%s, %s) RETURNING id;"
    )
    mock_raw_cursor.execute.assert_called_once_with(expected_sql, ["Apple", "iPhone 13"])
    assert wrapper.lastrowid == 42


def test_postgres_cursor_wrapper_does_not_duplicate_returning():
    """Verify that queries already containing 'RETURNING' are not duplicated."""
    mock_raw_cursor = MagicMock()
    mock_raw_cursor.fetchone.return_value = (99,)

    wrapper = PostgresCursorWrapper(mock_raw_cursor)
    wrapper.execute("INSERT INTO match_leads (score) VALUES (?) RETURNING id;", [85])

    mock_raw_cursor.execute.assert_called_once_with(
        "INSERT INTO match_leads (score) VALUES (%s) RETURNING id;", [85]
    )
    assert wrapper.lastrowid is None


def test_postgres_connection_wrapper():
    """Verify that PostgresConnectionWrapper delegates commit, rollback, and executescript."""
    mock_raw_conn = MagicMock()
    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    wrapper.commit()
    mock_raw_conn.commit.assert_called_once()

    wrapper.rollback()
    mock_raw_conn.rollback.assert_called_once()

    wrapper.executescript("CREATE TABLE test (id INT);")
    assert mock_raw_conn.cursor.called
    mock_raw_conn.commit.assert_called()


def test_postgres_connection_wrapper_context_manager_success():
    """Verify that PostgresConnectionWrapper commits on clean block exit."""
    mock_raw_conn = MagicMock()
    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    with wrapper as conn:
        assert conn is wrapper

    mock_raw_conn.commit.assert_called_once()
    mock_raw_conn.rollback.assert_not_called()


def test_postgres_connection_wrapper_context_manager_rollback_on_error():
    """Verify that PostgresConnectionWrapper rolls back on exception."""
    mock_raw_conn = MagicMock()
    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    with pytest.raises(ValueError, match="simulated failure"):
        with wrapper:
            raise ValueError("simulated failure")

    mock_raw_conn.rollback.assert_called_once()
    mock_raw_conn.commit.assert_not_called()


def test_postgres_connection_wrapper_matching_lifecycle(app):
    """
    Simulate full matching and handover transaction lifecycle under
    PostgresConnectionWrapper ensuring 'with db:' succeeds cleanly with
    PostgreSQL-style '%s' placeholder translation and context management.
    """
    from flask import g
    from database.db import get_db
    from matching.service import (
        find_and_record_matches,
        update_lead_review_status,
        issue_handover_token,
        redeem_handover_token,
    )

    class MockPsycopgCursor:
        def __init__(self, sqlite_cur):
            self._cur = sqlite_cur

        def execute(self, query, args=None):
            # Postgres receives '%s'; translate to '?' for test SQLite execution
            sqlite_sql = query.replace("%s", "?")
            return self._cur.execute(sqlite_sql, args or ())

        def executemany(self, query, seq):
            sqlite_sql = query.replace("%s", "?")
            return self._cur.executemany(sqlite_sql, seq)

        def fetchone(self):
            return self._cur.fetchone()

        def fetchall(self):
            return self._cur.fetchall()

        def close(self):
            self._cur.close()

        @property
        def rowcount(self):
            return self._cur.rowcount

        @property
        def description(self):
            return self._cur.description

    class MockPsycopgConnection:
        def __init__(self, sqlite_conn):
            self._conn = sqlite_conn
            self.committed = False
            self.rolled_back = False

        def cursor(self):
            return MockPsycopgCursor(self._conn.cursor())

        def commit(self):
            self.committed = True
            self._conn.commit()

        def rollback(self):
            self.rolled_back = True
            self._conn.rollback()

        def close(self):
            self._conn.close()

    with app.app_context():
        real_db = get_db()
        raw_mock_pg = MockPsycopgConnection(real_db)
        wrapper = PostgresConnectionWrapper(raw_mock_pg)
        g.db = wrapper

        # 1. Insert lost & found records using wrapper inside context manager
        with wrapper:
            c1 = wrapper.execute(
                """
                INSERT INTO private_electronics (
                    tracking_code, report_type, device_type, brand, model_family,
                    primary_color, campus_location, date_discovered,
                    distinctive_clues, reporter_contact, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "TRK-PG-TEST-L", "lost", "phone", "Apple", "iPhone 13",
                    "Blue", "Library", "2026-10-29",
                    "Owl decal on back case", "lost_owner@vit.edu", "open"
                )
            )
            lost_id = c1.lastrowid or 1

            c2 = wrapper.execute(
                """
                INSERT INTO private_electronics (
                    tracking_code, report_type, device_type, brand, model_family,
                    primary_color, campus_location, date_discovered,
                    distinctive_clues, reporter_contact, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "TRK-PG-TEST-F", "found", "phone", "Apple", "iPhone 13",
                    "Blue", "Library", "2026-10-29",
                    "Owl sticker on back case", "finder@vit.edu", "open"
                )
            )
            found_id = c2.lastrowid or 2

            # Create an admin user for approval actions
            wrapper.execute(
                """
                INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                ("pg_admin", "hash123", "PG Admin", "admin")
            )

        assert raw_mock_pg.committed is True

        # 2. Run matching engine (uses 'with db:' internally)
        leads = find_and_record_matches(lost_id)
        assert len(leads) >= 1
        lead_id = leads[0]["lead_id"]

        # 3. Update status to investigating (uses 'with db:' internally)
        ok, msg = update_lead_review_status(lead_id, "investigating", admin_id=1, admin_notes="Verified owl sticker")
        assert ok is True

        # 4. Issue handover token (uses 'with db:' internally)
        token_ok, token_msg, token = issue_handover_token(lead_id, admin_id=1)
        assert token_ok is True
        assert token is not None

        # 5. Redeem token at custody desk (uses 'with db:' internally)
        redeem_ok, redeem_msg, handover_data = redeem_handover_token(token, admin_id=1, resolution_notes="Verified in person")
        assert redeem_ok is True
        assert handover_data is not None


def test_report_electronics_safe_logging_on_matching_error(client, monkeypatch, caplog):
    """
    Verify that when matching fails, report_electronics logs an error
    without leaking private clues, brand, or contact details.
    """
    import logging
    from unittest.mock import patch

    secret_clue = "SecretOwlDecal999"
    student_contact = "alice.secret@vit.edu"

    with patch("matching.service.find_and_record_matches", side_effect=RuntimeError("Simulated matching engine outage")):
        with caplog.at_level(logging.ERROR):
            resp = client.post("/report/electronics", data={
                "report_type": "lost",
                "device_type": "phone",
                "brand": "Apple",
                "model_family": "iPhone 14",
                "primary_color": "Black",
                "campus_location": "Main Building",
                "date_discovered": "2026-10-29",
                "distinctive_clues": secret_clue,
                "reporter_contact": student_contact,
            })

            # Submitter still receives their confirmation receipt with code
            assert resp.status_code == 200
            assert b"YOUR PRIVATE TRACKING CODE" in resp.data

            # Check logged error: must record report ID and exception type, but NEVER secrets
            assert "Deterministic matching engine failed for report ID" in caplog.text
            assert "RuntimeError" in caplog.text
            assert secret_clue not in caplog.text
            assert student_contact not in caplog.text


def test_healthz_endpoint(client):
    """
    Verify that the production health check endpoint /healthz returns 200 OK
    and reveals zero internal details or secrets.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data == {"status": "ok"}
    # Must not contain version, debug, or sensitive keys
    assert "debug" not in data
    assert "database" not in data
