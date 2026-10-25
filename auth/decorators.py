"""
FindBack 2.0 - Server-Side RBAC & Authentication Decorators

Enforces that administrative access is validated against the database on every
request. Roles or active status stored in cookies are never trusted.
"""

from functools import wraps
from urllib.parse import urlparse
from flask import session, request, redirect, url_for, g, render_template, jsonify
from database.db import query_db

def is_safe_url(target: str) -> bool:
    """
    Validate that a redirect target URL is local and safe.
    Prevents open redirect attacks to arbitrary external websites.
    """
    if not target or not isinstance(target, str):
        return False
    # Must be a relative path starting with a single '/'
    target = target.strip()
    if target.startswith("//") or target.startswith("\\\\"):
        return False
    if not target.startswith("/"):
        return False
    # Ensure no scheme or network location is embedded
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == ""

def admin_required(roles=None):
    """
    Decorator for protected administrator endpoints.
    
    1. Validates session presence of non-sensitive admin_user_id.
    2. Queries SQLite database to verify account existence and is_active status.
    3. Verifies role against permitted roles list (defaults to ('admin', 'desk_staff')).
    4. Attaches verified admin record to Flask g.admin_user.
    5. Fails closed with 401/redirect or 403 on authorization failure.
    """
    if roles is None:
        roles = ("admin", "desk_staff")
    elif isinstance(roles, str):
        roles = (roles,)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            admin_user_id = session.get("admin_user_id")

            is_api = (
                request.is_json
                or request.path.startswith("/api/")
                or "application/json" in request.headers.get("Accept", "")
            )

            # 1. Unauthenticated check
            if not admin_user_id:
                if is_api:
                    return jsonify({"error": "Authentication required"}), 401
                # Preserve requested path if safe
                next_url = request.path if is_safe_url(request.path) else None
                return redirect(url_for("admin_login", next=next_url))

            # 2. Database validation on every protected request (Anti-Obscurity / Anti-Cookie Trust)
            user = query_db(
                """
                SELECT id, username, full_name, role, is_active
                FROM admin_users
                WHERE id = ?
                """,
                [admin_user_id],
                one=True,
            )

            # Fail closed: account missing or inactive
            if not user or user["is_active"] != 1:
                session.clear()
                if is_api:
                    return jsonify({"error": "Account inactive or unauthorized"}), 401
                return redirect(url_for("admin_login"))

            # 3. Role-Based Access Control (RBAC) check
            user_role = user["role"]
            if user_role not in roles:
                return (
                    render_template(
                        "errors/403.html",
                        error_message="Access denied: Your account role does not have permission to view this resource.",
                    ),
                    403,
                )

            # Attach verified database record to request context
            g.admin_user = user
            return f(*args, **kwargs)

        return decorated_function
    return decorator
