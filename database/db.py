"""
FindBack 2.0 - Database Helper Functions

This module provides unified connection management, initialization, and safe
parameterized query utilities. It seamlessly supports:
1. SQLite (default local development and automated testing)
2. PostgreSQL (managed persistent cloud storage, e.g. Neon or Supabase)

Raw SQL string interpolation is strictly prohibited.
"""

import os
import re
import sqlite3
from pathlib import Path
from flask import g, current_app

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_PG_PATH = Path(__file__).resolve().parent / "schema_pg.sql"

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def is_postgres_uri(uri: str) -> bool:
    """Return True if the database URI points to a PostgreSQL instance."""
    if not uri or not isinstance(uri, str):
        return False
    return uri.startswith("postgresql://") or uri.startswith("postgres://")


def adapt_query_for_postgres(query: str) -> str:
    """
    Translate standard SQLite '?' parameter placeholders to PostgreSQL '%s'.
    """
    return query.replace("?", "%s")


class PostgresCursorWrapper:
    """
    Cursor wrapper providing SQLite-compatible API over psycopg2 cursor.
    Enforces '?' placeholder translation, provides dict-like row access,
    and emulates 'lastrowid' via automatic RETURNING id on INSERT statements.
    """

    def __init__(self, raw_cursor):
        self._cursor = raw_cursor
        self.lastrowid = None

    def execute(self, query, args=None):
        adapted = adapt_query_for_postgres(query)
        stripped = adapted.strip()
        upper_query = stripped.upper()
        is_insert = upper_query.startswith("INSERT INTO")
        has_returning = "RETURNING" in upper_query

        # If insert without explicit RETURNING, append RETURNING id to capture lastrowid
        if is_insert and not has_returning:
            adapted = stripped.rstrip(" ;") + " RETURNING id;"

        self._cursor.execute(adapted, args or ())

        if is_insert and not has_returning:
            try:
                row = self._cursor.fetchone()
                if row is not None:
                    # DictCursor allows indexing by 0 or 'id'
                    self.lastrowid = row[0]
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None

        return self

    def executemany(self, query, seq_of_args):
        adapted = adapt_query_for_postgres(query)
        self._cursor.executemany(adapted, seq_of_args)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description


class PostgresConnectionWrapper:
    """
    Connection wrapper providing SQLite-compatible API over psycopg2 connection.
    Enforces cursor wrapping, connection-level execute shortcut, and script execution.
    """

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor())

    def execute(self, query, args=None):
        cur = self.cursor()
        cur.execute(query, args)
        return cur

    def executescript(self, script: str):
        cur = self._conn.cursor()
        cur.execute(script)
        self._conn.commit()
        cur.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    """
    Open or reuse a database connection for the current application context.
    Seamlessly selects SQLite or PostgreSQL based on application configuration.
    """
    if "db" not in g:
        db_uri = current_app.config.get("DATABASE", "findback.db")

        if is_postgres_uri(db_uri):
            if not HAS_PSYCOPG2:
                raise RuntimeError(
                    "PostgreSQL database configured via DATABASE_URL, but 'psycopg2' is not installed. "
                    "Ensure 'psycopg2-binary' is installed in the active environment."
                )
            # Normalize postgres:// to postgresql:// for psycopg2
            if db_uri.startswith("postgres://"):
                db_uri = "postgresql://" + db_uri[len("postgres://"):]
            raw_conn = psycopg2.connect(db_uri, cursor_factory=DictCursor)
            g.db = PostgresConnectionWrapper(raw_conn)
        else:
            g.db = sqlite3.connect(db_uri)
            g.db.row_factory = sqlite3.Row
            # Crucial security setting: enforce foreign keys in SQLite
            g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db_schema(db=None):
    """Execute schema.sql (SQLite) or schema_pg.sql (PostgreSQL) to create all tables."""
    if db is None:
        db = get_db()

    db_uri = current_app.config.get("DATABASE", "findback.db")

    schema_file = SCHEMA_PG_PATH if is_postgres_uri(db_uri) else SCHEMA_PATH

    with open(schema_file, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()


def query_db(query, args=(), one=False):
    """
    Execute a parameterized SQL query safely.
    Uses '?' parameter substitution, automatically adapted for PostgreSQL when running on Postgres.
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), commit=True):
    """
    Execute an INSERT, UPDATE, or DELETE query parameterized safely.
    Returns the cursor for accessing lastrowid or rowcount.
    """
    db = get_db()
    cur = db.execute(query, args)
    if commit:
        db.commit()
    return cur


def init_app(app):
    """Register database teardown functions with the Flask application."""
    app.teardown_appcontext(close_db)
