"""
FindBack 2.0 - Matching Integration & Dispute Service

Coordinates matching execution, duplicate prevention, item-level dispute
detection, and atomic transaction updates for private electronics.
"""

import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from database.db import get_db, query_db
from matching.matcher import compute_score, PROVISIONAL_LEAD_THRESHOLD
from matching.explainer import generate_breakdown, serialize_breakdown

ALLOWED_REVIEW_STATUSES = ("investigating", "disputed", "dismissed", "pending_review")

def find_and_record_matches(new_report_id: int, db=None) -> list:
    """
    Evaluate candidate matches for a newly inserted private electronics report.
    
    1. Fetches new report and candidate opposite reports.
    2. Runs deterministic scoring.
    3. If score >= PROVISIONAL_LEAD_THRESHOLD:
       - Checks for item-level competing claims.
       - Wraps lead insertion and status updates in a single SQLite transaction.
       - If competing claims detected, marks lead and item as 'disputed' to freeze handover.
    """
    if db is None:
        db = get_db()

    # 1. Fetch the newly inserted report
    new_report = query_db(
        "SELECT * FROM private_electronics WHERE id = ?",
        [new_report_id],
        one=True,
    )
    if not new_report:
        return []

    new_type = new_report["report_type"]
    opposite_type = "found" if new_type == "lost" else "lost"

    # 2. Query open / active candidate reports of opposite type with compatible device type
    candidates = query_db(
        """
        SELECT * FROM private_electronics
        WHERE report_type = ? AND device_type = ? AND status != 'resolved'
        """,
        [opposite_type, new_report["device_type"]],
    )

    created_leads = []

    for cand in candidates:
        if new_type == "lost":
            lost_rep = dict(new_report)
            found_rep = dict(cand)
        else:
            lost_rep = dict(cand)
            found_rep = dict(new_report)

        lost_id = lost_rep["id"]
        found_id = found_rep["id"]

        # 3. Compute deterministic score
        score_result = compute_score(lost_rep, found_rep)

        if not score_result["match_possible"] or score_result["total_score"] < PROVISIONAL_LEAD_THRESHOLD:
            continue

        # 4. Duplicate lead prevention (check before insert)
        existing = query_db(
            "SELECT id FROM match_leads WHERE lost_report_id = ? AND found_report_id = ?",
            [lost_id, found_id],
            one=True,
        )
        if existing:
            continue

        # 5. Detect item-level competing claims
        # A conflict occurs if this found item already has an active lead with another lost item,
        # OR this lost item already has an active lead with another found item.
        competing_leads = query_db(
            """
            SELECT id, lost_report_id, found_report_id FROM match_leads
            WHERE review_status != 'dismissed'
              AND (
                  (found_report_id = ? AND lost_report_id != ?)
                  OR
                  (lost_report_id = ? AND found_report_id != ?)
              )
            """,
            [found_id, lost_id, lost_id, found_id],
        )

        is_disputed = len(competing_leads) > 0
        lead_status = "disputed" if is_disputed else "pending_review"

        breakdown = generate_breakdown(lost_rep, found_rep, score_result)
        breakdown_json = serialize_breakdown(breakdown)

        # 6. Atomic SQLite Transaction
        # All lead insertions and status updates execute together or roll back on error.
        with db:
            cur = db.execute(
                """
                INSERT INTO match_leads (
                    lost_report_id, found_report_id, match_score,
                    score_breakdown_json, review_status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    lost_id,
                    found_id,
                    score_result["total_score"],
                    breakdown_json,
                    lead_status,
                ),
            )
            lead_id = cur.lastrowid

            if is_disputed:
                # Collect all item IDs involved in competing leads
                all_involved_item_ids = {lost_id, found_id}
                for c in competing_leads:
                    all_involved_item_ids.add(c["lost_report_id"])
                    all_involved_item_ids.add(c["found_report_id"])

                # Flag all competing leads as disputed
                db.execute(
                    """
                    UPDATE match_leads
                    SET review_status = 'disputed', updated_at = CURRENT_TIMESTAMP
                    WHERE review_status != 'dismissed'
                      AND (found_report_id = ? OR lost_report_id = ?)
                    """,
                    [found_id, lost_id],
                )
                # Flag ALL involved underlying electronics items as disputed
                for item_id in all_involved_item_ids:
                    db.execute(
                        """
                        UPDATE private_electronics
                        SET status = 'disputed'
                        WHERE id = ?
                        """,
                        [item_id],
                    )
            else:
                # Update item status from 'open' to 'lead_identified'
                db.execute(
                    """
                    UPDATE private_electronics
                    SET status = 'lead_identified'
                    WHERE (id = ? OR id = ?) AND status = 'open'
                    """,
                    [lost_id, found_id],
                )

        created_leads.append(
            {
                "lead_id": lead_id,
                "lost_report_id": lost_id,
                "found_report_id": found_id,
                "score": score_result["total_score"],
                "review_status": lead_status,
                "is_disputed": is_disputed,
            }
        )

    return created_leads

def can_lead_proceed_to_handover(lead_id: int, db=None) -> tuple:
    """
    Check if a match lead is eligible to proceed to handover token generation.
    Returns (eligible: bool, reason: str).
    
    DISPUTE INVARIANT:
    Disputed items and disputed leads are strictly FROZEN from handover token generation.
    """
    if db is None:
        db = get_db()

    lead = query_db(
        "SELECT * FROM match_leads WHERE id = ?",
        [lead_id],
        one=True,
    )
    if not lead:
        return False, "Match lead not found."

    if lead["review_status"] == "disputed":
        return (
            False,
            "Handover blocked: This match lead is flagged as disputed due to competing claims.",
        )

    if lead["review_status"] == "dismissed":
        return False, "Handover blocked: This match lead was dismissed."

    # Check underlying items
    lost_item = query_db(
        "SELECT status FROM private_electronics WHERE id = ?",
        [lead["lost_report_id"]],
        one=True,
    )
    found_item = query_db(
        "SELECT status FROM private_electronics WHERE id = ?",
        [lead["found_report_id"]],
        one=True,
    )

    if not lost_item or not found_item:
        return False, "Handover blocked: Referenced item record missing."

    if lost_item["status"] == "disputed" or found_item["status"] == "disputed":
        return (
            False,
            "Handover blocked: An underlying item record is flagged as disputed.",
        )

    if lost_item["status"] == "resolved" or found_item["status"] == "resolved":
        return False, "Handover blocked: Item is already marked resolved."

    return True, "Eligible for staff handover review."


# ----------------------------------------------------------------------
# Single-Use Handover Token Lifecycle & Service Logic (Phase 8)
# ----------------------------------------------------------------------

def generate_handover_token() -> str:
    """
    Generate an unpredictable, cryptographically secure single-use handover token.
    Uses Python's secrets module with URL-safe entropy.
    Format: HND-<random_chars>
    """
    return f"HND-{secrets.token_urlsafe(8)}"


def hash_handover_token(token: str) -> str:
    """Compute deterministic SHA-256 hash of the handover token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def issue_handover_token(lead_id: int, admin_id: int, db=None) -> tuple:
    """
    Issue an expiring, single-use handover token for an approved match lead.

    Enforces:
    1. Pre-condition checks via can_lead_proceed_to_handover().
    2. Generating unpredictable token via secrets module.
    3. Hashing token with SHA-256 (raw token NEVER stored in database).
    4. Enforcing 30-minute expiry window.
    5. Atomic transaction: updates match lead to 'approved' and inserts handover log.

    Returns:
        (success: bool, message: str, raw_token: str | None)
    """
    if db is None:
        db = get_db()

    # 1. Enforce dispute freeze and eligibility guard
    eligible, reason = can_lead_proceed_to_handover(lead_id, db=db)
    if not eligible:
        return False, reason, None

    # 2. Fetch lead details
    lead = query_db(
        "SELECT id, lost_report_id, found_report_id, review_status FROM match_leads WHERE id = ?",
        [lead_id],
        one=True,
    )
    if not lead:
        return False, "Match lead not found.", None

    if lead["review_status"] == "disputed":
        return False, "Handover blocked: Lead is flagged as disputed due to competing claims.", None

    # 3. Check for existing active, unexpired, unused token for this lead
    now_utc = datetime.now(timezone.utc)
    existing_tokens = query_db(
        """
        SELECT id, token_expires_at, token_used_at
        FROM handover_logs
        WHERE match_id = ? AND token_used_at IS NULL
        """,
        [lead_id],
    )
    for tok in existing_tokens:
        try:
            exp_dt = datetime.fromisoformat(tok["token_expires_at"])
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now_utc <= exp_dt:
                return (
                    False,
                    "An active, unexpired handover token has already been generated for this lead. Awaiting custody desk redemption.",
                    None,
                )
        except Exception:
            pass

    # 4. Generate token and hash
    raw_token = generate_handover_token()
    token_hash = hash_handover_token(raw_token)
    expires_at = (now_utc + timedelta(minutes=30)).isoformat()

    # 5. Atomic SQLite transaction
    with db:
        # Update lead review_status to 'approved'
        db.execute(
            """
            UPDATE match_leads
            SET review_status = 'approved',
                assigned_admin_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND review_status != 'disputed'
            """,
            [admin_id, lead_id],
        )

        # Insert audit record with token_hash (raw token is never persisted)
        db.execute(
            """
            INSERT INTO handover_logs (
                item_type, item_id, match_id, token_hash,
                token_expires_at, token_used_at, admin_id, resolution_notes
            ) VALUES ('electronics', ?, ?, ?, ?, NULL, ?, 'Token issued by authorized administrator upon lead approval.')
            """,
            (lead["found_report_id"], lead_id, token_hash, expires_at, admin_id),
        )

    return True, "Handover token generated successfully.", raw_token


def redeem_handover_token(
    raw_token: str,
    admin_id: int,
    resolution_notes: str = None,
    db=None,
) -> tuple:
    """
    Verify and redeem a single-use handover token at the custody desk.

    Enforces:
    1. Token presence and format check.
    2. SHA-256 hash lookup in handover_logs.
    3. Single-use enforcement (token_used_at must be NULL).
    4. Expiration check (current time <= token_expires_at).
    5. Dispute recheck: neither match_lead nor underlying items can be disputed.
    6. Atomic SQLite transaction to prevent double-redemption race conditions.
    7. Updates item statuses to 'resolved' and records token_used_at.

    Returns:
        (success: bool, message: str, handover_data: dict | None)
    """
    if db is None:
        db = get_db()

    if not raw_token or not isinstance(raw_token, str) or not raw_token.strip():
        return False, "Handover token is required.", None

    clean_token = raw_token.strip()
    token_hash = hash_handover_token(clean_token)

    # Query handover log joined with lead and item status
    record = query_db(
        """
        SELECT hl.id, hl.item_type, hl.item_id, hl.match_id, hl.token_hash,
               hl.token_expires_at, hl.token_used_at,
               ml.lost_report_id, ml.found_report_id, ml.review_status,
               lost.status AS lost_status, found.status AS found_status,
               found.brand, found.model_family, found.primary_color, found.device_type
        FROM handover_logs hl
        LEFT JOIN match_leads ml ON hl.match_id = ml.id
        LEFT JOIN private_electronics lost ON ml.lost_report_id = lost.id
        LEFT JOIN private_electronics found ON ml.found_report_id = found.id
        WHERE hl.token_hash = ?
        """,
        [token_hash],
        one=True,
    )

    if not record:
        return False, "Invalid or unknown handover token.", None

    # Check if already consumed
    if record["token_used_at"] is not None:
        return (
            False,
            "Handover token has already been used and cannot be reused (Single-Use Token Violation).",
            None,
        )

    # Check 30-minute expiration window
    now_utc = datetime.now(timezone.utc)
    try:
        exp_dt = datetime.fromisoformat(record["token_expires_at"])
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if now_utc > exp_dt:
            return (
                False,
                "Handover token has expired (30-minute validity exceeded). A new token must be authorized.",
                None,
            )
    except Exception:
        return False, "Malformed token expiration metadata.", None

    # Recheck dispute freeze at redemption point
    if (
        record["review_status"] == "disputed"
        or record["lost_status"] == "disputed"
        or record["found_status"] == "disputed"
    ):
        return (
            False,
            "Handover blocked: An involved record has been flagged as disputed due to competing claims.",
            None,
        )

    # Atomic compare-and-swap redemption
    now_str = now_utc.isoformat()
    notes = (
        resolution_notes.strip()
        if resolution_notes and resolution_notes.strip()
        else "In-person desk verification completed and custody released."
    )

    with db:
        # Atomic check-and-set: ensure token_used_at IS NULL
        cur = db.execute(
            """
            UPDATE handover_logs
            SET token_used_at = ?,
                admin_id = ?,
                resolution_notes = ?
            WHERE id = ? AND token_used_at IS NULL
            """,
            (now_str, admin_id, notes, record["id"]),
        )
        if cur.rowcount == 0:
            return (
                False,
                "Handover token has already been used and cannot be reused (Concurrent Claim Prevented).",
                None,
            )

        # Update lead review status to approved
        if record["match_id"]:
            db.execute(
                """
                UPDATE match_leads
                SET review_status = 'approved', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                [record["match_id"]],
            )

        # Update all referenced electronics item records to 'resolved'
        involved_ids = set()
        if record["item_id"]:
            involved_ids.add(record["item_id"])
        if record["lost_report_id"]:
            involved_ids.add(record["lost_report_id"])
        if record["found_report_id"]:
            involved_ids.add(record["found_report_id"])

        for iid in involved_ids:
            db.execute(
                """
                UPDATE private_electronics
                SET status = 'resolved'
                WHERE id = ?
                """,
                [iid],
            )

    return (
        True,
        "Handover successfully completed and recorded in custody audit logs.",
        {
            "log_id": record["id"],
            "item_id": record["item_id"],
            "used_at": now_str,
            "device_summary": f"{record['brand']} {record['model_family'] or ''} ({record['primary_color']})".strip(),
        },
    )


# ----------------------------------------------------------------------
# Human Review & Dispute Adjudication Logic (Phase 8)
# ----------------------------------------------------------------------

def update_lead_review_status(
    lead_id: int,
    new_status: str,
    admin_id: int,
    admin_notes: str = None,
    db=None,
) -> tuple:
    """
    Update a match lead's review status with strict state transition validation.

    Enforces:
    1. Allowlist validation: ('investigating', 'disputed', 'dismissed', 'pending_review').
       ('approved' must go through issue_handover_token()).
    2. Dispute lock: cannot unfreeze or clear dispute while competing active leads remain.
    3. When dismissing a competing lead: if no competing active leads remain,
       automatically clears dispute status on the remaining lead and underlying items.
    4. Atomic transaction.
    """
    if db is None:
        db = get_db()

    if new_status not in ALLOWED_REVIEW_STATUSES:
        return (
            False,
            f"Invalid review status '{new_status}'. Allowed statuses: {', '.join(ALLOWED_REVIEW_STATUSES)}.",
        )

    lead = query_db(
        "SELECT id, lost_report_id, found_report_id, review_status FROM match_leads WHERE id = ?",
        [lead_id],
        one=True,
    )
    if not lead:
        return False, "Match lead not found."

    lost_id = lead["lost_report_id"]
    found_id = lead["found_report_id"]

    # Prevent bypassing dispute lock: if currently disputed and attempting to set to
    # investigating or pending_review, verify if other active competing leads still exist
    if lead["review_status"] == "disputed" and new_status in ("investigating", "pending_review"):
        other_active = query_db(
            """
            SELECT id FROM match_leads
            WHERE review_status != 'dismissed'
              AND id != ?
              AND (found_report_id = ? OR lost_report_id = ?)
            """,
            [lead_id, found_id, lost_id],
        )
        if other_active:
            return (
                False,
                "Cannot clear dispute flag while competing active claims exist. Adjudicate and dismiss invalid candidate claims first.",
            )

    with db:
        db.execute(
            """
            UPDATE match_leads
            SET review_status = ?,
                admin_notes = COALESCE(?, admin_notes),
                assigned_admin_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, admin_notes or None, admin_id, lead_id),
        )

        if new_status == "disputed":
            # Flag underlying items as disputed
            db.execute(
                "UPDATE private_electronics SET status = 'disputed' WHERE id IN (?, ?)",
                [lost_id, found_id],
            )
        elif new_status == "dismissed":
            # Collect all items connected to the conflict group
            affected_leads = query_db(
                """
                SELECT id, lost_report_id, found_report_id
                FROM match_leads
                WHERE found_report_id = ? OR lost_report_id = ?
                """,
                [found_id, lost_id],
            )
            all_item_ids = {found_id, lost_id}
            for al in affected_leads:
                all_item_ids.add(al["lost_report_id"])
                all_item_ids.add(al["found_report_id"])

            for item_id in all_item_ids:
                remaining_competing = query_db(
                    """
                    SELECT id FROM match_leads
                    WHERE review_status != 'dismissed'
                      AND (found_report_id = ? OR lost_report_id = ?)
                    """,
                    [item_id, item_id],
                )
                if len(remaining_competing) <= 1:
                    # Item no longer has multiple competing claims!
                    db.execute(
                        """
                        UPDATE private_electronics
                        SET status = 'lead_identified'
                        WHERE id = ? AND status = 'disputed'
                        """,
                        [item_id],
                    )
                    # If this item has exactly 1 remaining active lead, check if that lead is clear on both ends
                    if len(remaining_competing) == 1:
                        rem_lead_id = remaining_competing[0]["id"]
                        rem_lead = query_db(
                            "SELECT lost_report_id, found_report_id FROM match_leads WHERE id = ?",
                            [rem_lead_id],
                            one=True,
                        )
                        if rem_lead:
                            other_end_conflicts = query_db(
                                """
                                SELECT id FROM match_leads
                                WHERE review_status != 'dismissed'
                                  AND id != ?
                                  AND (found_report_id = ? OR lost_report_id = ?)
                                """,
                                [rem_lead_id, rem_lead["found_report_id"], rem_lead["lost_report_id"]],
                            )
                            if not other_end_conflicts:
                                db.execute(
                                    """
                                    UPDATE match_leads
                                    SET review_status = 'investigating', updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ? AND review_status = 'disputed'
                                    """,
                                    [rem_lead_id],
                                )

    return True, f"Match lead #{lead_id} review status updated to '{new_status}'."


def get_lead_details(lead_id: int, db=None) -> dict | None:
    """Fetch complete side-by-side details for a single match lead."""
    if db is None:
        db = get_db()

    row = query_db(
        """
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
        WHERE ml.id = ?
        """,
        [lead_id],
        one=True,
    )
    if not row:
        return None

    lead = dict(row)
    try:
        lead["breakdown"] = json.loads(lead["score_breakdown_json"])
    except Exception:
        lead["breakdown"] = {}

    return lead


def get_all_disputed_groups(db=None) -> list:
    """Query and group all disputed candidate match leads by found item."""
    if db is None:
        db = get_db()

    rows = query_db(
        """
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
        WHERE ml.review_status = 'disputed' OR lost.status = 'disputed' OR found.status = 'disputed'
        ORDER BY ml.found_report_id, ml.match_score DESC
        """
    )

    groups = {}
    for r in rows:
        lead = dict(r)
        try:
            lead["breakdown"] = json.loads(lead["score_breakdown_json"])
        except Exception:
            lead["breakdown"] = {}

        fid = lead["found_report_id"]
        if fid not in groups:
            groups[fid] = {
                "found_id": fid,
                "found_device": f"{lead['brand']} {lead['model_family'] or ''} ({lead['primary_color']})".strip(),
                "found_location": lead["found_location"],
                "found_date": lead["found_date"],
                "found_clues": lead["found_clues"],
                "found_contact": lead["found_contact"],
                "leads": [],
            }
        groups[fid]["leads"].append(lead)

    return list(groups.values())


def get_recent_handovers(limit: int = 15, db=None) -> list:
    """Fetch recent verified item handovers for the desk audit trail."""
    if db is None:
        db = get_db()

    rows = query_db(
        """
        SELECT hl.id, hl.item_type, hl.item_id, hl.match_id, hl.token_expires_at,
               hl.token_used_at, hl.resolution_notes, hl.created_at,
               au.username AS officer_username, au.full_name AS officer_name,
               pe.device_type, pe.brand, pe.model_family, pe.primary_color
        FROM handover_logs hl
        JOIN admin_users au ON hl.admin_id = au.id
        LEFT JOIN private_electronics pe ON hl.item_id = pe.id
        WHERE hl.token_used_at IS NOT NULL
        ORDER BY hl.token_used_at DESC
        LIMIT ?
        """,
        [limit],
    )
    return [dict(r) for r in rows]

