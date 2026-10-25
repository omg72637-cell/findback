"""
FindBack 2.0 - Core Flask Application

Implements:
1. Public ordinary-item listings and allowlist validation (Workflow A).
2. Confidential electronics reporting with credential heuristic defense (Workflow B).
3. Cryptographic private tracking-code generation.
4. Anti-oracle status lookup.
5. Strict zero-leakage boundaries on all public routes and error handlers.
"""

import json
import re
import secrets
from datetime import date
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g
)
from werkzeug.security import check_password_hash
from config import Config
from database.db import init_app as init_db_app, query_db, execute_db
from auth.csrf import generate_csrf_token, csrf_protect
from auth.decorators import admin_required, is_safe_url
from matching.service import (
    can_lead_proceed_to_handover,
    issue_handover_token,
    redeem_handover_token,
    update_lead_review_status,
    get_lead_details,
    get_all_disputed_groups,
    get_recent_handovers,
    ALLOWED_REVIEW_STATUSES,
)

# Hardcoded 7-category ordinary item allowlist (DEC-03)
ORDINARY_ALLOWLIST = (
    "Water Bottles & Mugs",
    "Notebooks, Binders & Textbooks",
    "Umbrellas",
    "Eyeglasses & Sunglasses",
    "Non-Electronic Stationery",
    "Outerwear, Jackets & Scarves",
    "General Bags & Backpacks (Non-Electronic)",
)

# Allowed electronic device categories for confidential reports
ALLOWED_DEVICE_TYPES = (
    ("phone", "Smartphone / Cellphone"),
    ("laptop", "Laptop / Notebook PC"),
    ("tablet", "Tablet / iPad"),
    ("earbuds", "Wireless Earbuds / Headphones"),
    ("charger", "Power Adapter / Charger"),
    ("smartwatch", "Smartwatch / Fitness Tracker"),
)
DEVICE_TYPE_KEYS = frozenset(k for k, _ in ALLOWED_DEVICE_TYPES)

# Heuristic pattern to catch common passwords, PINs, or recovery phrases
PROHIBITED_CREDENTIAL_PATTERN = re.compile(
    r"\b(pin|password|passcode|pattern\s*lock|screen\s*lock|recovery\s*code|unlock\s*code)\b",
    re.IGNORECASE,
)

def detect_prohibited_credentials(text: str) -> bool:
    """
    Heuristic check to catch obvious password or PIN keywords in user submissions.
    
    IMPORTANT LIMITATION & DISCLAIMER:
    Keyword and regex pattern scanning is a heuristic check, NOT a complete or
    infallible security filter. A user could describe secrets in unusual phrasing
    that no regex can reliably detect. It is used strictly as a best-effort,
    defense-in-depth guardrail to catch inadvertent submissions. The primary
    defense remains clear, prominent UI microcopy.
    """
    if not text:
        return False
    return bool(PROHIBITED_CREDENTIAL_PATTERN.search(text))

def generate_tracking_code() -> str:
    """
    Generate an unguessable, cryptographically secure private tracking code.
    Uses Python's secrets module with 32 bytes of URL-safe entropy.
    """
    return f"TRK-{secrets.token_urlsafe(32)}"

def create_app(test_config=None):
    """Application factory for FindBack 2.0."""
    app = Flask(__name__)

    app.config.from_object(Config)
    if test_config is not None:
        app.config.from_mapping(test_config)
        if not app.config.get("SECRET_KEY"):
            app.config["SECRET_KEY"] = "testing-secret-key-minimum-32-chars-long"

    # Register database teardown
    init_db_app(app)

    # Register session-bound CSRF token generator for templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf_token)

    # -------------------------------------------------------------
    # Public Ordinary Items Routes (Workflow A)
    # -------------------------------------------------------------

    @app.route("/")
    def index():
        """
        Public Feed: displays available ordinary items only.
        STRICT PRIVACY INVARIANT: Uses explicit column projection.
        Excludes contact_email and has zero access to private_electronics.
        """
        category = request.args.get("category", "").strip()
        search_query = request.args.get("q", "").strip()

        sql = """
            SELECT id, category, description, campus_location, date_discovered, status
            FROM ordinary_items
            WHERE status = 'available'
        """
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        if search_query:
            sql += " AND (description LIKE ? OR campus_location LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        sql += " ORDER BY id DESC"

        items = query_db(sql, params)

        return render_template(
            "index.html",
            items=items,
            allowlist_categories=ORDINARY_ALLOWLIST,
            current_category=category,
            search_query=search_query,
        )

    @app.route("/report")
    def report_choice():
        """Workflow Selector Gateway: explains Public vs. Confidential flows."""
        return render_template("report_choice.html")

    @app.route("/report/ordinary", methods=["GET", "POST"])
    def report_ordinary():
        """
        Ordinary Item Reporting Route.
        Enforces category allowlist on POST. Returns HTTP 400 on violations.
        """
        if request.method == "POST":
            report_type = request.form.get("report_type", "").strip()
            category = request.form.get("category", "").strip()
            description = request.form.get("description", "").strip()
            campus_location = request.form.get("campus_location", "").strip()
            date_discovered = request.form.get("date_discovered", "").strip()
            contact_email = request.form.get("contact_email", "").strip()

            # Server-side Category Allowlist Validation
            if category not in ORDINARY_ALLOWLIST:
                return (
                    render_template(
                        "errors/400.html",
                        error_message=f"Category '{category}' is not on the approved ordinary allowlist. Electronics must be reported via the confidential workflow.",
                    ),
                    400,
                )

            # Report type validation
            if report_type not in ("lost", "found"):
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Invalid report type. Must be 'lost' or 'found'.",
                    ),
                    400,
                )

            # Basic presence and length validation
            if not description or not campus_location or not contact_email:
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Description, campus location, and contact email are required.",
                    ),
                    400,
                )

            if len(description) > 500 or len(campus_location) > 100 or len(contact_email) > 100:
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Submitted text exceeds permissible field length limits.",
                    ),
                    400,
                )

            # Safe parameterized insertion
            execute_db(
                """
                INSERT INTO ordinary_items (
                    report_type, category, description, campus_location,
                    date_discovered, status, contact_email
                ) VALUES (?, ?, ?, ?, ?, 'available', ?)
                """,
                (
                    report_type,
                    category,
                    description,
                    campus_location,
                    date_discovered or str(date.today()),
                    contact_email,
                ),
            )

            flash("Ordinary item report successfully published to the campus board.", "success")
            return redirect(url_for("index"))

        return render_template(
            "report_ordinary.html",
            allowlist_categories=ORDINARY_ALLOWLIST,
            today_date=str(date.today()),
        )

    # -------------------------------------------------------------
    # Confidential Electronics Reporting (Workflow B) - Phase 5
    # -------------------------------------------------------------

    @app.route("/report/electronics", methods=["GET", "POST"])
    def report_electronics():
        """
        Confidential Electronics Reporting Route.
        - Captures structured device attributes and safe ownership clues.
        - Enforces prohibited credential checks (PINs, passwords, biometrics).
        - Generates private cryptographic tracking code.
        - Displays tracking code once on receipt. NEVER published publicly.
        """
        if request.method == "POST":
            report_type = request.form.get("report_type", "").strip()
            device_type = request.form.get("device_type", "").strip()
            brand = request.form.get("brand", "").strip()
            model_family = request.form.get("model_family", "").strip()
            primary_color = request.form.get("primary_color", "").strip()
            campus_location = request.form.get("campus_location", "").strip()
            date_discovered = request.form.get("date_discovered", "").strip()
            distinctive_clues = request.form.get("distinctive_clues", "").strip()
            reporter_contact = request.form.get("reporter_contact", "").strip()

            # Validation: Report Type
            if report_type not in ("lost", "found"):
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Invalid report type. Must be 'lost' or 'found'.",
                    ),
                    400,
                )

            # Validation: Device Type compatibility gate
            if device_type not in DEVICE_TYPE_KEYS:
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Invalid device type selected. Choose from the approved device categories.",
                    ),
                    400,
                )

            # Validation: Presence checks
            if not brand or not primary_color or not campus_location or not distinctive_clues or not reporter_contact:
                return (
                    render_template(
                        "errors/400.html",
                        error_message="All required device details, clues, and contact fields must be provided.",
                    ),
                    400,
                )

            # Validation: Safe length limits
            if (
                len(brand) > 50
                or len(model_family) > 50
                or len(primary_color) > 30
                or len(campus_location) > 100
                or len(distinctive_clues) > 500
                or len(reporter_contact) > 100
            ):
                return (
                    render_template(
                        "errors/400.html",
                        error_message="Input text exceeds maximum allowable field lengths.",
                    ),
                    400,
                )

            # Prohibited Credential Heuristic Guardrail
            # Evaluates all free-text fields for obvious PIN / password patterns
            suspect_fields = [distinctive_clues, brand, model_family, reporter_contact]
            if any(detect_prohibited_credentials(field) for field in suspect_fields):
                return (
                    render_template(
                        "errors/400.html",
                        error_message=(
                            "Prohibited credential pattern detected. For student safety, "
                            "never enter device unlock PINs, passwords, pattern locks, or recovery keys. "
                            "Campus desk staff will verify custody using non-secret visual traits only."
                        ),
                    ),
                    400,
                )

            # Generate unguessable private tracking code
            tracking_code = generate_tracking_code()

            # Insert into private_electronics
            # STRICT INVARIANT: never logged to application logs or console
            cur = execute_db(
                """
                INSERT INTO private_electronics (
                    tracking_code, report_type, device_type, brand, model_family,
                    primary_color, campus_location, date_discovered,
                    distinctive_clues, reporter_contact, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """,
                (
                    tracking_code,
                    report_type,
                    device_type,
                    brand,
                    model_family,
                    primary_color,
                    campus_location,
                    date_discovered or str(date.today()),
                    distinctive_clues,
                    reporter_contact,
                ),
            )
            new_report_id = cur.lastrowid

            # Trigger deterministic matching engine
            try:
                from matching.service import find_and_record_matches
                find_and_record_matches(new_report_id)
            except Exception:
                # Security rule: never expose internal matching exceptions to the user
                pass

            # Render confirmation receipt displaying code once to submitter
            return render_template(
                "report_electronics_success.html",
                tracking_code=tracking_code,
            )

        return render_template(
            "report_electronics.html",
            allowed_device_types=ALLOWED_DEVICE_TYPES,
            today_date=str(date.today()),
        )

    # -------------------------------------------------------------
    # Private Status Lookup (Anti-Oracle Design) - Phase 5
    # -------------------------------------------------------------

    @app.route("/status", methods=["GET", "POST"])
    def status_lookup():
        """
        Private Report Status Lookup Route.
        - Accepts private tracking code via POST (preferred) or GET.
        - Strictly projects ONLY `status` column from database.
        - Employs anti-oracle defense: returns uniform generic message
          for missing, malformed, or non-matching codes. Never confirms database existence.
        - Explains that tracking code is a lookup credential, not proof of ownership.
        """
        tracking_code = None
        if request.method == "POST":
            tracking_code = request.form.get("tracking_code", "").strip()
        else:
            tracking_code = request.args.get("tracking_code", "").strip()

        if not tracking_code:
            return render_template("status_lookup.html", query_performed=False)

        # Validate input format and safe length
        if len(tracking_code) > 120 or not tracking_code.startswith("TRK-"):
            # Anti-oracle: uniform generic not-found message
            return render_template(
                "status_lookup.html",
                query_performed=True,
                status_found=False,
                submitted_code="",
            )

        # Strict Query Projection: SELECT id, status ONLY
        # Contact information, distinctive clues, and locations are NEVER fetched or exposed.
        row = query_db(
            "SELECT id, status FROM private_electronics WHERE tracking_code = ?",
            [tracking_code],
            one=True,
        )

        if not row:
            # Anti-oracle: identical generic message, does not reveal record non-existence
            return render_template(
                "status_lookup.html",
                query_performed=True,
                status_found=False,
                submitted_code="",
            )

        # Map internal status to authorized student-facing progress label
        db_status = row["status"]

        # If lead is under staff review, check if an authorized lead was approved for handover (Step 4)
        if db_status == "lead_identified":
            approved_lead = query_db(
                """
                SELECT id FROM match_leads
                WHERE (lost_report_id = ? OR found_report_id = ?)
                  AND review_status = 'approved'
                """,
                [row["id"], row["id"]],
                one=True,
            )
            if approved_lead:
                db_status = "ready_for_handover"

        status_map = {
            "open": {
                "label": "Submitted (Searching for Match)",
                "badge": "pending",
                "step": 2,
                "guidance": "Your report is securely recorded. Our deterministic engine is actively comparing it against candidate reports.",
            },
            "lead_identified": {
                "label": "Under Staff Review",
                "badge": "warning",
                "step": 3,
                "guidance": "A candidate match lead was identified. Authorized campus desk staff are reviewing non-secret clues to verify custody.",
            },
            "disputed": {
                "label": "Under Staff Review (Competing Claim)",
                "badge": "danger",
                "step": 3,
                "guidance": "Multiple reports have matching traits. Automated progression is frozen while campus staff conduct a neutral human review.",
            },
            "ready_for_handover": {
                "label": "Ready for Desk Handover",
                "badge": "available",
                "step": 4,
                "guidance": "Desk staff have verified this lead. Please visit the Central Custody Desk in person with your Student ID to complete custody release.",
            },
            "resolved": {
                "label": "Case Resolved",
                "badge": "resolved",
                "step": 5,
                "guidance": "This item has been safely returned to its verified owner.",
            },
        }

        info = status_map.get(
            db_status,
            {
                "label": "Under Staff Review",
                "badge": "pending",
                "step": 2,
                "guidance": "Campus staff are evaluating your report.",
            },
        )

        return render_template(
            "status_lookup.html",
            query_performed=True,
            status_found=True,
            status_label=info["label"],
            status_badge_class=info["badge"],
            current_step=info["step"],
            guidance_text=info["guidance"],
            submitted_code=tracking_code,
        )

    # -------------------------------------------------------------
    # Administrator Authentication & Control Center (Phase 7)
    # -------------------------------------------------------------

    @app.route("/admin/login", methods=["GET", "POST"])
    @csrf_protect
    def admin_login():
        """
        Staff Authentication Endpoint (DEC-07 Approved).
        - GET: displays login form with session CSRF token.
        - POST: verifies credentials against database. Stores ONLY admin_user_id.
        - Employs generic error response against user enumeration.
        - Sanitizes redirect target against open redirect attacks using is_safe_url().
        """
        # If already logged in and active, redirect to dashboard or safe next_url
        if session.get("admin_user_id"):
            user = query_db(
                "SELECT id, is_active FROM admin_users WHERE id = ?",
                [session["admin_user_id"]],
                one=True,
            )
            if user and user["is_active"] == 1:
                next_param = request.args.get("next") or request.form.get("next")
                if next_param and is_safe_url(next_param):
                    return redirect(next_param)
                return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            next_url = request.form.get("next", "").strip()

            # Input validation: presence
            if not username or not password:
                return (
                    render_template(
                        "admin/login.html",
                        error_message="Invalid credentials or inactive account.",
                        next_url=next_url if is_safe_url(next_url) else None,
                    ),
                    400,
                )

            # Retrieve user by username using parameterized query
            user = query_db(
                """
                SELECT id, username, password_hash, full_name, role, is_active
                FROM admin_users
                WHERE username = ?
                """,
                [username],
                one=True,
            )

            # Verify credentials and active status
            # Generic error response avoids user enumeration (anti-oracle)
            if not user or not check_password_hash(user["password_hash"], password) or user["is_active"] != 1:
                return (
                    render_template(
                        "admin/login.html",
                        error_message="Invalid credentials or inactive account.",
                        next_url=next_url if is_safe_url(next_url) else None,
                    ),
                    401,
                )

            # Clear session to prevent session fixation attacks
            session.clear()

            # DEC-07: Store ONLY admin_user_id in session cookie
            # Roles, permissions, and active status are NEVER stored in cookies
            session["admin_user_id"] = user["id"]

            flash(f"Welcome back, {user['full_name']}.", "success")

            # Open redirect defense: sanitize next_url
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard"))

        # GET request
        next_url = request.args.get("next", "").strip()
        return render_template(
            "admin/login.html",
            next_url=next_url if is_safe_url(next_url) else None,
        )

    @app.route("/admin", endpoint="admin_dashboard")
    @admin_required()
    def admin_dashboard():
        """
        Administrator Control Center (Phase 7).
        Protected by @admin_required() - queries database on every request.
        Renders dashboard with verified admin user details from g.admin_user.
        """
        return render_template("admin/dashboard.html", admin_user=g.admin_user)

    @app.route("/admin/leads", endpoint="admin_leads")
    @admin_required(roles=("admin", "desk_staff"))
    def admin_leads():
        """
        Administrator Match Review Queue (Phase 8).
        Protected by @admin_required(roles=('admin', 'desk_staff')).
        Lists candidate leads identified by deterministic matching engine with
        side-by-side clues and factor breakdowns.
        """
        filter_status = request.args.get("status", "").strip()

        sql = """
            SELECT ml.id, ml.lost_report_id, ml.found_report_id, ml.match_score,
                   ml.score_breakdown_json, ml.review_status, ml.admin_notes, ml.updated_at,
                   lost.device_type, lost.brand, lost.model_family, lost.primary_color,
                   lost.campus_location AS lost_location, lost.date_discovered AS lost_date,
                   lost.distinctive_clues AS lost_clues, lost.reporter_contact AS lost_contact,
                   lost.status AS lost_status,
                   found.campus_location AS found_location, found.date_discovered AS found_date,
                   found.distinctive_clues AS found_clues, found.reporter_contact AS found_contact,
                   found.status AS found_status
            FROM match_leads ml
            JOIN private_electronics lost ON ml.lost_report_id = lost.id
            JOIN private_electronics found ON ml.found_report_id = found.id
        """
        params = []
        if filter_status and filter_status in ALLOWED_REVIEW_STATUSES:
            sql += " WHERE ml.review_status = ?"
            params.append(filter_status)

        sql += " ORDER BY ml.match_score DESC, ml.id DESC"

        rows = query_db(sql, params)
        leads = []
        for r in rows:
            lead = dict(r)
            try:
                lead["breakdown"] = json.loads(lead["score_breakdown_json"])
            except Exception:
                lead["breakdown"] = {}
            leads.append(lead)

        return render_template(
            "admin/leads.html",
            leads=leads,
            current_filter=filter_status,
        )

    @app.route("/admin/leads/<int:lead_id>/status", methods=["POST"], endpoint="admin_lead_status")
    @admin_required(roles="admin")
    @csrf_protect
    def admin_lead_status(lead_id: int):
        """
        Human Review Status Transition Endpoint (Phase 8).
        Strictly restricted to 'admin' role. Desk staff receive HTTP 403.
        Validates requested status transition against explicit server-side allowlist.
        Preserves item-level dispute lock.
        """
        new_status = request.form.get("status", "").strip()
        admin_notes = request.form.get("notes", "").strip()

        if new_status not in ALLOWED_REVIEW_STATUSES:
            return (
                render_template(
                    "errors/400.html",
                    error_message=f"Invalid review status '{new_status}'. Permitted statuses: {', '.join(ALLOWED_REVIEW_STATUSES)}.",
                ),
                400,
            )

        success, message = update_lead_review_status(
            lead_id=lead_id,
            new_status=new_status,
            admin_id=g.admin_user["id"],
            admin_notes=admin_notes,
        )

        if not success:
            flash(message, "danger")
            return redirect(url_for("admin_leads"))

        flash(message, "success")
        return redirect(url_for("admin_leads"))

    @app.route("/admin/leads/<int:lead_id>/approve", methods=["POST"], endpoint="admin_lead_approve")
    @admin_required(roles="admin")
    @csrf_protect
    def admin_lead_approve(lead_id: int):
        """
        Lead Approval & Handover Token Issuance Endpoint (Phase 8).
        Strictly restricted to 'admin' role. Desk staff receive HTTP 403.
        Verifies can_lead_proceed_to_handover() dispute guard.
        Generates unpredictable token, stores SHA-256 hash in handover_logs,
        and displays raw token ONCE on confirmation receipt.
        """
        # Pre-check dispute eligibility
        can_proceed, reason = can_lead_proceed_to_handover(lead_id)
        if not can_proceed:
            return (
                render_template(
                    "errors/400.html",
                    error_message=reason,
                ),
                400,
            )

        success, message, raw_token = issue_handover_token(
            lead_id=lead_id,
            admin_id=g.admin_user["id"],
        )

        if not success:
            return (
                render_template(
                    "errors/400.html",
                    error_message=message,
                ),
                400,
            )

        # Render one-time receipt screen
        return render_template(
            "admin/token_issued.html",
            lead_id=lead_id,
            raw_token=raw_token,
        )

    @app.route("/admin/disputes", endpoint="admin_disputes")
    @admin_required(roles=("admin", "desk_staff"))
    def admin_disputes():
        """
        Disputed Claims Adjudication View (Phase 8).
        Displays multi-claimant conflicts where automatic handover is locked.
        """
        disputed_groups = get_all_disputed_groups()
        return render_template(
            "admin/disputes.html",
            disputed_groups=disputed_groups,
        )

    @app.route("/admin/handover", methods=["GET", "POST"], endpoint="admin_handover")
    @admin_required(roles=("admin", "desk_staff"))
    @csrf_protect
    def admin_handover():
        """
        Supervised Handover Custody Desk (Phase 8).
        Authorized for both 'admin' and 'desk_staff' roles.
        - GET: Displays verification checklist and recent audit trail.
        - POST: Verifies submitted single-use token hash, enforces single-use,
                checks 30-minute expiry, prevents race conditions, and marks
                items 'resolved' in an atomic transaction.
        """
        if request.method == "POST":
            token = request.form.get("token", "").strip()
            resolution_notes = request.form.get("resolution_notes", "").strip()

            if not token:
                recent_handovers = get_recent_handovers()
                return (
                    render_template(
                        "admin/handover.html",
                        recent_handovers=recent_handovers,
                        error_message="Handover token is required.",
                    ),
                    400,
                )

            success, message, handover_data = redeem_handover_token(
                raw_token=token,
                admin_id=g.admin_user["id"],
                resolution_notes=resolution_notes,
            )

            recent_handovers = get_recent_handovers()

            if not success:
                return (
                    render_template(
                        "admin/handover.html",
                        recent_handovers=recent_handovers,
                        error_message=message,
                    ),
                    400,
                )

            return render_template(
                "admin/handover.html",
                recent_handovers=recent_handovers,
                success_message=message,
            )

        recent_handovers = get_recent_handovers()
        return render_template(
            "admin/handover.html",
            recent_handovers=recent_handovers,
        )

    @app.route("/admin/logout", methods=["POST"])
    @csrf_protect
    def admin_logout():
        """
        Administrator Logout Endpoint.
        Enforces POST-only method (GET returns HTTP 405 Method Not Allowed).
        Protected by session-bound CSRF token.
        Clears the entire session and redirects to the public home page.
        """
        session.clear()
        flash("You have been signed out of the staff portal.", "info")
        return redirect(url_for("index"))

    # -------------------------------------------------------------
    # Error Handlers (Zero-Leakage Invariants)
    # -------------------------------------------------------------

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Strict security rule: never expose internal stack traces or SQLite errors
        return render_template("errors/500.html"), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
