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
