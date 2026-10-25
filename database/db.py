"""
FindBack 2.0 - Database Helper Functions

This module provides SQLite connection management, initialization, and safe
parameterized query utilities. Raw SQL string interpolation is strictly prohibited.
"""

import sqlite3
from pathlib import Path
from flask import g, current_app

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db():
    """
    Open or reuse a SQLite database connection for the current application context.
    Enforces foreign key constraints and dictionary-like row behavior.
    """
    if "db" not in g:
        db_path = current_app.config.get("DATABASE", "findback.db")
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # Crucial security setting: enforce foreign keys in SQLite
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the SQLite database connection if open."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_schema(db=None):
    """Execute schema.sql to create all tables."""
    if db is None:
        db = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()

def query_db(query, args=(), one=False):
    """
    Execute a parameterized SQL query safely.
    Always uses '?' parameter substitution to defend against SQL injection.
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
