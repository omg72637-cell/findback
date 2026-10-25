"""
FindBack 2.0 - Lightweight Session-Bound CSRF Protection

Zero external dependencies: uses Python's secrets and hmac standard libraries.
Enforces constant-time token comparison to protect against timing attacks.
"""

import hmac
import secrets
from functools import wraps
from flask import session, request, abort, render_template, current_app

def generate_csrf_token() -> str:
    """
    Generate or retrieve a cryptographically secure, session-bound CSRF token.
    The token is stored in the signed session cookie and validated on POST requests.
    """
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]

def validate_csrf_token() -> bool:
    """
    Validate incoming request's CSRF token against the session-bound token.
    Uses constant-time comparison via hmac.compare_digest.
    """
    # Allow test suite to explicitly toggle CSRF testing if configured
    if current_app.config.get("TESTING") and current_app.config.get("WTF_CSRF_ENABLED") is False:
        return True

    expected = session.get("_csrf_token")
    if not expected:
        return False

    # Check form body first, then fallback to HTTP request header
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not submitted:
        return False

    return hmac.compare_digest(str(submitted).strip(), str(expected).strip())

def csrf_protect(f):
    """
    Decorator for state-changing endpoints (POST/PUT/DELETE).
    Rejects missing or invalid CSRF tokens with HTTP 400.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not validate_csrf_token():
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Invalid or missing CSRF token. State-changing requests must include a valid session token.",
                    ),
                    400,
                )
        return f(*args, **kwargs)
    return decorated_function
