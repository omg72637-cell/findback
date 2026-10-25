"""
FindBack 2.0 - Database Initialization and Synthetic Seeding Script

Initializes the local SQLite or cloud PostgreSQL database schema and populates
it with safe, fictitious demonstration items and initial administrative user accounts.
"""

import os
import sqlite3
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash
from database.db import (
    is_postgres_uri,
    HAS_PSYCOPG2,
    PostgresConnectionWrapper,
    SCHEMA_PATH,
    SCHEMA_PG_PATH,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "findback.db"

def load_dotenv(env_path: Path = BASE_DIR / ".env") -> None:
    """
    Minimal, zero-dependency helper to read a local .env file into os.environ.
    Preserves any environment variables already set in the current process.
    """
    if not env_path.is_file():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass

def init_database(db_path=None, load_env=True):
    """
    Initialize tables and insert initial test fixture records.

    Args:
        db_path: Path or connection string. If None, uses DATABASE_URL
                 or DATABASE environment variable or defaults to findback.db.
        load_env: Whether to attempt loading variables from local .env if present.
    """
    if load_env:
        load_dotenv()

    db_uri = db_path or os.environ.get("DATABASE_URL") or os.environ.get("DATABASE") or str(DB_PATH)

    if is_postgres_uri(str(db_uri)):
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "PostgreSQL database configured via DATABASE_URL, but 'psycopg2' is not installed. "
                "Ensure 'psycopg2-binary' is installed in the active environment."
            )
        import psycopg2
        from psycopg2.extras import DictCursor
        conn_str = str(db_uri)
        if conn_str.startswith("postgres://"):
            conn_str = "postgresql://" + conn_str[len("postgres://"):]
        print("Initializing PostgreSQL database schema via DATABASE_URL...")
        raw_conn = psycopg2.connect(conn_str, cursor_factory=DictCursor)
        conn = PostgresConnectionWrapper(raw_conn)
        schema_file = SCHEMA_PG_PATH
    else:
        db_path_obj = Path(db_uri)
        print(f"Initializing SQLite database at: {db_path_obj}")
        conn = sqlite3.connect(db_path_obj)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        schema_file = SCHEMA_PATH

    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        cur = conn.cursor()

        # Check if admin user already exists
        cur.execute("SELECT id FROM admin_users WHERE username = ?", ["admin"])
        if not cur.fetchone():
            admin_pass = os.environ.get("INITIAL_ADMIN_PASSWORD")
            if not admin_pass:
                raise ValueError(
                    "Missing required environment variable 'INITIAL_ADMIN_PASSWORD'. "
                    "An initial password must be set before creating the 'admin' account."
                )
            hashed = generate_password_hash(admin_pass)
            cur.execute(
                """
                INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                ("admin", hashed, "Campus Security Admin", "admin")
            )
            print("Created default admin user: 'admin'")

        # Check if desk_staff user already exists
        cur.execute("SELECT id FROM admin_users WHERE username = ?", ["desk_staff"])
        if not cur.fetchone():
            desk_pass = os.environ.get("INITIAL_DESK_STAFF_PASSWORD")
            if not desk_pass:
                raise ValueError(
                    "Missing required environment variable 'INITIAL_DESK_STAFF_PASSWORD'. "
                    "An initial password must be set before creating the 'desk_staff' account."
                )
            hashed_desk = generate_password_hash(desk_pass)
            cur.execute(
                """
                INSERT INTO admin_users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                ("desk_staff", hashed_desk, "Central Desk Officer", "desk_staff")
            )
            print("Created default desk staff user: 'desk_staff'")

        # Check if ordinary items already exist
        cur.execute("SELECT COUNT(*) as count FROM ordinary_items")
        count_row = cur.fetchone()
        count = count_row["count"] if hasattr(count_row, "keys") and "count" in count_row.keys() else count_row[0]
        if count == 0:
            sample_ordinary = [
                (
                    "found",
                    "Water Bottles & Mugs",
                    "Blue 750ml stainless-steel insulated flask with small dent on bottom rim",
                    "Central Library, 2nd Floor Reading Room",
                    "2026-10-23",
                    "available",
                    "library.desk@campus.local"
                ),
                (
                    "found",
                    "Umbrellas",
                    "Black compact automatic folding umbrella with wooden handle",
                    "Science Block C, Ground Floor Hallway",
                    "2026-10-22",
                    "available",
                    "science.desk@campus.local"
                ),
                (
                    "found",
                    "Eyeglasses & Sunglasses",
                    "Black wire-frame reading glasses in brown protective case",
                    "Cafeteria West Wing Table 14",
                    "2026-10-21",
                    "available",
                    "cafeteria.staff@campus.local"
                ),
                (
                    "lost",
                    "Notebooks, Binders & Textbooks",
                    "Red spiral notebook containing Engineering Mechanics notes and sketches",
                    "Mechanical Workshop Room 102",
                    "2026-10-20",
                    "available",
                    "student1@campus.local"
                )
            ]
            cur.executemany(
                """
                INSERT INTO ordinary_items (
                    report_type, category, description, campus_location,
                    date_discovered, status, contact_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                sample_ordinary
            )
            print(f"Seeded {len(sample_ordinary)} ordinary test items.")

        conn.commit()
    finally:
        conn.close()

    print("Database initialization complete.")

if __name__ == "__main__":
    target_db = None
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print("Usage: python database/init_db.py [optional_path_or_db_url]")
            sys.exit(0)
        target_db = sys.argv[1]
    init_database(db_path=target_db)
