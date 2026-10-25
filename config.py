"""
FindBack 2.0 - Application Configuration

This module manages environment variables and security settings for FindBack 2.0.
In compliance with project safety rules, the SECRET_KEY must never use an insecure
default fallback value. If missing, the application halts immediately with a clear error.
"""

import os
from pathlib import Path
from datetime import timedelta

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent

def load_dotenv(env_path: Path = BASE_DIR / ".env") -> None:
    """
    Minimal, zero-dependency helper to read a local .env file into os.environ.
    This avoids adding external packages while keeping development setup simple.
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

# Attempt to load local .env if present
load_dotenv()

class Config:
    """Base application configuration class."""
    
    # Retrieve secret key from environment
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set it before starting the application. "
            "You can generate one using: python -c 'import secrets; print(secrets.token_hex(32))'"
        )

    # Database location: supports DATABASE_URL (e.g. Neon/Supabase PostgreSQL) or local SQLite
    DATABASE = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE", str(BASE_DIR / "findback.db"))

    # Security: Session cookie hardening
    # Prevents client-side scripts from reading the session cookie (XSS protection)
    SESSION_COOKIE_HTTPONLY = True
    
    # Restricts cookie sending on cross-site requests (CSRF protection)
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Session lifespan (60 minutes of inactivity)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    
    # Set to True in production with HTTPS
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"

class TestConfig(Config):
    """Configuration for automated test fixtures."""
    TESTING = True
    DATABASE = ":memory:"
    DATABASE_URL = ":memory:"
