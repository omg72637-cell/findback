"""
FindBack 2.0 - Phase 6 Deterministic Matching & Dispute Unit Tests

Verifies:
1. Compatible reports produce deterministic scoring.
2. Individual factors contribute according to documented weights (DEC-12).
3. Incompatible device types gate-stops scoring (score = 0).
4. Missing, None, or malformed inputs do not crash the matcher.
5. Provisional threshold (85 pts) behaves as documented.
6. Repeated matching prevents duplicate leads.
7. Competing claims detected at item level and flag 'disputed'.
8. Atomic transaction safety during dispute handling.
9. Disputed items and leads blocked from handover progression.
10. Public routes never expose match scores, evidence, or lead breakdowns.
"""

import pytest
from matching.matcher import (
    compute_score,
    PROVISIONAL_LEAD_THRESHOLD,
    WEIGHT_DEVICE_TYPE,
    WEIGHT_BRAND,
    WEIGHT_COLOR,
    WEIGHT_LOCATION,
    WEIGHT_TIME_WINDOW,
)
from matching.explainer import generate_breakdown, serialize_breakdown, deserialize_breakdown
from matching.service import find_and_record_matches, can_lead_proceed_to_handover
from database.db import get_db, query_db, execute_db

# ---------------------------------------------------------------------------
# 1. Deterministic Scoring Reproducibility
# ---------------------------------------------------------------------------

def test_deterministic_scoring_reproducibility():
    """
    DETERMINISM TEST: Ensure calling compute_score 50 times with identical
    data returns the exact same score and breakdown every time.
    """
    lost = {
        "device_type": "phone",
        "brand": "Apple",
        "model_family": "iPhone 13",
        "primary_color": "Midnight Blue",
        "campus_location": "Main Library",
        "date_discovered": "2026-10-20",
    }
    found = {
        "device_type": "phone",
        "brand": "Apple",
        "model_family": "iPhone 13",
        "primary_color": "Midnight Blue",
        "campus_location": "Main Library",
        "date_discovered": "2026-10-21",
    }

    first_result = compute_score(lost, found)
    assert first_result["match_possible"] is True
    assert first_result["total_score"] == 100

    for _ in range(50):
        res = compute_score(lost, found)
        assert res["total_score"] == first_result["total_score"]
        assert res["match_possible"] == first_result["match_possible"]
        assert res["factors"] == first_result["factors"]

# ---------------------------------------------------------------------------
# 2. Factor Weight Contributions (DEC-12)
# ---------------------------------------------------------------------------

def test_factor_weights_contribution():
    """
    Verify each factor awards points exactly according to documented rules:
    Type: 30, Brand: 25, Color: 15, Location: 15, Time Window: 15.
    """
    base_lost = {
        "device_type": "phone",
        "brand": "Samsung",
        "primary_color": "Black",
        "campus_location": "Science Block",
        "date_discovered": "2026-10-20",
    }
    base_found = {
        "device_type": "phone",
        "brand": "Samsung",
        "primary_color": "Black",
        "campus_location": "Science Block",
        "date_discovered": "2026-10-21",  # 1 day delta -> 15 pts
    }

    # 1. Full Match: 30 + 25 + 15 + 15 + 15 = 100
    res = compute_score(base_lost, base_found)
    assert res["total_score"] == 100
    assert res["factors"]["device_type"]["earned"] == 30
    assert res["factors"]["brand"]["earned"] == 25
    assert res["factors"]["color"]["earned"] == 15
    assert res["factors"]["location"]["earned"] == 15
    assert res["factors"]["time_window"]["earned"] == 15

    # 2. Different brand (loses 25 pts) -> 75 pts
    diff_brand = dict(base_found, brand="Sony")
    res_b = compute_score(base_lost, diff_brand)
    assert res_b["total_score"] == 75
    assert res_b["factors"]["brand"]["earned"] == 0

    # 3. Different color (loses 15 pts) -> 85 pts
    diff_color = dict(base_found, primary_color="White")
    res_c = compute_score(base_lost, diff_color)
    assert res_c["total_score"] == 85
    assert res_c["factors"]["color"]["earned"] == 0

    # 4. Different location (loses 15 pts) -> 85 pts
    diff_loc = dict(base_found, campus_location="Sports Complex")
    res_l = compute_score(base_lost, diff_loc)
    assert res_l["total_score"] == 85
    assert res_l["factors"]["location"]["earned"] == 0

    # 5. Time window decay
    # 5 days delta -> 10 pts
    t_5d = dict(base_found, date_discovered="2026-10-25")
    assert compute_score(base_lost, t_5d)["factors"]["time_window"]["earned"] == 10

    # 10 days delta -> 5 pts
    t_10d = dict(base_found, date_discovered="2026-10-30")
    assert compute_score(base_lost, t_10d)["factors"]["time_window"]["earned"] == 5

    # Found before lost (negative delta) -> 0 pts
    t_neg = dict(base_found, date_discovered="2026-10-15")
    assert compute_score(base_lost, t_neg)["factors"]["time_window"]["earned"] == 0

# ---------------------------------------------------------------------------
# 3. Incompatible Device Type Gate
# ---------------------------------------------------------------------------

def test_incompatible_device_type_gate():
    """
    MANDATORY GATE: Incompatible device types (phone vs laptop) must
    immediately evaluate to total_score = 0, match_possible = False.
    """
    lost_phone = {
        "device_type": "phone",
        "brand": "Apple",
        "primary_color": "Silver",
        "campus_location": "Library",
        "date_discovered": "2026-10-20",
    }
    found_laptop = {
        "device_type": "laptop",
        "brand": "Apple",
        "primary_color": "Silver",
        "campus_location": "Library",
        "date_discovered": "2026-10-20",
    }
    res = compute_score(lost_phone, found_laptop)
    assert res["match_possible"] is False
    assert res["total_score"] == 0
    assert res["factors"]["device_type"]["earned"] == 0
    assert "Incompatible" in res["summary"]

# ---------------------------------------------------------------------------
# 4. Missing, None, and Malformed Inputs
# ---------------------------------------------------------------------------

def test_malformed_and_missing_inputs_safety():
    """Ensure missing keys, None values, and malformed dates do not crash matcher."""
    empty_res = compute_score({}, {})
    assert empty_res["match_possible"] is False
    assert empty_res["total_score"] == 0

    bad_date = {
        "device_type": "phone",
        "brand": "Apple",
        "date_discovered": "invalid-date-string",
    }
    good_phone = {
        "device_type": "phone",
        "brand": "Apple",
        "date_discovered": "2026-10-20",
    }
    res = compute_score(bad_date, good_phone)
    assert res["match_possible"] is True
    assert res["factors"]["time_window"]["earned"] == 0

# ---------------------------------------------------------------------------
# 5. Provisional Threshold Lead Generation
# ---------------------------------------------------------------------------

def test_provisional_threshold_lead_generation(app):
    """
    Verify reports meeting provisional threshold (>=85) generate match leads,
    while reports below threshold (<85) do not.
    """
    with app.app_context():
        db = get_db()
        # Seed lost phone
        c1 = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-LOST-THRESH-1', 'lost', 'phone', 'Apple', 'iPhone 13',
                     'Midnight Blue', 'Central Library', '2026-10-20', 'Clues', 'a@test.local', 'open')
            """
        )
        lost_id = c1.lastrowid

        # Seed found phone with matching traits (score >= 85)
        c2 = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-FOUND-THRESH-1', 'found', 'phone', 'Apple', 'iPhone 13',
                     'Midnight Blue', 'Central Library', '2026-10-21', 'Clues', 'b@test.local', 'open')
            """
        )
        found_id = c2.lastrowid

        # Seed another found phone with poor traits (score < 85: different brand, color, loc)
        c3 = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-FOUND-POOR-1', 'found', 'phone', 'Google', 'Pixel 7',
                     'White', 'Cafeteria', '2026-10-21', 'Clues', 'c@test.local', 'open')
            """
        )
        poor_found_id = c3.lastrowid

        # Trigger matching for lost_id
        leads = find_and_record_matches(lost_id)
        assert len(leads) == 1
        assert leads[0]["found_report_id"] == found_id
        assert leads[0]["score"] >= PROVISIONAL_LEAD_THRESHOLD

        # Confirm no lead was generated for poor_found_id
        poor_lead = query_db(
            "SELECT id FROM match_leads WHERE lost_report_id = ? AND found_report_id = ?",
            [lost_id, poor_found_id],
            one=True,
        )
        assert poor_lead is None

# ---------------------------------------------------------------------------
# 6. Duplicate Lead Prevention
# ---------------------------------------------------------------------------

def test_duplicate_lead_prevention(app):
    """Verify executing find_and_record_matches repeatedly does not create duplicate leads."""
    with app.app_context():
        db = get_db()
        c1 = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-DUP-L', 'lost', 'phone', 'Apple', 'iPhone 13',
                     'Blue', 'Library', '2026-10-20', 'Clues', 'a@test.local', 'open')
            """
        )
        lost_id = c1.lastrowid

        c2 = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-DUP-F', 'found', 'phone', 'Apple', 'iPhone 13',
                     'Blue', 'Library', '2026-10-21', 'Clues', 'b@test.local', 'open')
            """
        )
        found_id = c2.lastrowid

        # Run 1
        leads_1 = find_and_record_matches(lost_id)
        assert len(leads_1) == 1

        # Run 2 (duplicate execution)
        leads_2 = find_and_record_matches(lost_id)
        assert len(leads_2) == 0

        # Verify only 1 row exists in match_leads
        total = query_db(
            "SELECT COUNT(*) as count FROM match_leads WHERE lost_report_id = ? AND found_report_id = ?",
            [lost_id, found_id],
            one=True,
        )
        assert total["count"] == 1

# ---------------------------------------------------------------------------
# 7. Item-Level Competing Claims & Dispute Flagging
# ---------------------------------------------------------------------------

def test_item_level_competing_claim_detection(app):
    """
    COMPETING CLAIM INVARIANT:
    When two lost reports match the same found item (conflict on item level),
    both leads and all affected item records must be flagged as 'disputed'.
    """
    with app.app_context():
        db = get_db()
        # Single physical found iPhone turned in to desk
        c_found = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-FOUND-ITEM-1', 'found', 'phone', 'Apple', 'iPhone 13',
                     'Black', 'Cafeteria', '2026-10-22', 'Found on table', 'finder@test.local', 'open')
            """
        )
        found_id = c_found.lastrowid

        # Student A reports lost iPhone matching found item
        c_lost_a = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-LOST-STUDENT-A', 'lost', 'phone', 'Apple', 'iPhone 13',
                     'Black', 'Cafeteria', '2026-10-21', 'My phone', 'studentA@test.local', 'open')
            """
        )
        lost_a_id = c_lost_a.lastrowid

        # Match Student A -> Single clean lead (pending_review)
        leads_a = find_and_record_matches(lost_a_id)
        assert len(leads_a) == 1
        assert leads_a[0]["review_status"] == "pending_review"
        assert leads_a[0]["is_disputed"] is False

        # Student B now also reports a matching lost iPhone for the SAME found item!
        c_lost_b = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-LOST-STUDENT-B', 'lost', 'phone', 'Apple', 'iPhone 13',
                     'Black', 'Cafeteria', '2026-10-21', 'Also my phone', 'studentB@test.local', 'open')
            """
        )
        lost_b_id = c_lost_b.lastrowid

        # Match Student B -> Conflict detected! Competing claim on item found_id
        leads_b = find_and_record_matches(lost_b_id)
        assert len(leads_b) == 1
        assert leads_b[0]["review_status"] == "disputed"
        assert leads_b[0]["is_disputed"] is True

        # Verify that Student A's existing lead was ALSO updated to 'disputed'
        lead_a_row = query_db(
            "SELECT review_status FROM match_leads WHERE lost_report_id = ? AND found_report_id = ?",
            [lost_a_id, found_id],
            one=True,
        )
        assert lead_a_row["review_status"] == "disputed"

        # Verify that all involved items are marked 'disputed' in private_electronics
        f_row = query_db("SELECT status FROM private_electronics WHERE id = ?", [found_id], one=True)
        la_row = query_db("SELECT status FROM private_electronics WHERE id = ?", [lost_a_id], one=True)
        lb_row = query_db("SELECT status FROM private_electronics WHERE id = ?", [lost_b_id], one=True)
        assert f_row["status"] == "disputed"
        assert la_row["status"] == "disputed"
        assert lb_row["status"] == "disputed"

# ---------------------------------------------------------------------------
# 8. Dispute Progression Blocked from Handover
# ---------------------------------------------------------------------------

def test_dispute_atomic_transaction_rollback_on_failure(app, monkeypatch):
    """
    ATOMIC TRANSACTION INVARIANT:
    If a database error occurs during dispute updates, the transaction
    must roll back completely, leaving no orphan leads or corrupted statuses.
    """
    with app.app_context():
        db = get_db()
        c_l = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-TX-LOST', 'lost', 'phone', 'Apple', 'iPhone 13',
                     'Black', 'Library', '2026-10-20', 'Clues', 'tx1@test.local', 'open')
            """
        )
        lost_id = c_l.lastrowid

        c_f = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-TX-FOUND', 'found', 'phone', 'Apple', 'iPhone 13',
                     'Black', 'Library', '2026-10-21', 'Clues', 'tx2@test.local', 'open')
            """
        )
        found_id = c_f.lastrowid

        # Monkeypatch serialize_breakdown to raise a simulated runtime error inside the transaction block
        import matching.service as s_mod
        def mock_broken_serialize(*args, **kwargs):
            raise RuntimeError("Simulated transaction fault")

        monkeypatch.setattr(s_mod, "serialize_breakdown", mock_broken_serialize)

        with pytest.raises(RuntimeError, match="Simulated transaction fault"):
            find_and_record_matches(lost_id, db=db)

        # Verify rollback: 0 match leads created
        lead_count = query_db(
            "SELECT COUNT(*) as cnt FROM match_leads WHERE lost_report_id = ? AND found_report_id = ?",
            [lost_id, found_id],
            one=True,
        )
        assert lead_count["cnt"] == 0

        # Verify item statuses remained 'open' (not modified)
        lost_item = query_db("SELECT status FROM private_electronics WHERE id = ?", [lost_id], one=True)
        found_item = query_db("SELECT status FROM private_electronics WHERE id = ?", [found_id], one=True)
        assert lost_item["status"] == "open"
        assert found_item["status"] == "open"

def test_disputed_lead_blocked_from_handover(app):
    """
    SAFETY INVARIANT:
    A match lead marked 'disputed' cannot generate a handover token or proceed to custody release.
    """
    with app.app_context():
        db = get_db()
        c_l = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-DISP-L', 'lost', 'laptop', 'Dell', 'XPS', 'Silver', 'Lab', '2026-10-20', 'c', 'c@t.local', 'disputed')
            """
        )
        c_f = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-DISP-F', 'found', 'laptop', 'Dell', 'XPS', 'Silver', 'Lab', '2026-10-21', 'c', 'f@t.local', 'disputed')
            """
        )
        c_lead = db.execute(
            """
            INSERT INTO match_leads (
                lost_report_id, found_report_id, match_score,
                score_breakdown_json, review_status
            ) VALUES (?, ?, 95, '{"breakdown": "test"}', 'disputed')
            """,
            (c_l.lastrowid, c_f.lastrowid),
        )
        disputed_lead_id = c_lead.lastrowid

        eligible, reason = can_lead_proceed_to_handover(disputed_lead_id)
        assert eligible is False
        assert "disputed" in reason.lower()

# ---------------------------------------------------------------------------
# 9. Public Routes Never Expose Matching Evidence
# ---------------------------------------------------------------------------

def test_zero_leakage_of_match_evidence(client, app):
    """
    Ensure match leads, points, and score breakdowns never appear
    in public responses (GET / or GET /status).
    """
    with app.app_context():
        db = get_db()
        c_l = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-MATCH-SECRET', 'lost', 'phone', 'Apple', 'iPhone 15',
                     'Titanium', 'Auditorium', '2026-10-24', 'Secret Wallpaper', 'secret@test.local', 'open')
            """
        )
        c_f = db.execute(
            """
            INSERT INTO private_electronics (
                tracking_code, report_type, device_type, brand, model_family,
                primary_color, campus_location, date_discovered,
                distinctive_clues, reporter_contact, status
            ) VALUES ('TRK-MATCH-SECRET-F', 'found', 'phone', 'Apple', 'iPhone 15',
                     'Titanium', 'Auditorium', '2026-10-24', 'Secret Wallpaper', 'finder@test.local', 'open')
            """
        )
        find_and_record_matches(c_l.lastrowid)

    # Check Public feed
    resp_feed = client.get("/")
    assert b"score_breakdown" not in resp_feed.data
    assert b"iPhone 15" not in resp_feed.data
    assert b"Secret Wallpaper" not in resp_feed.data

    # Check Status lookup
    resp_status = client.post("/status", data={"tracking_code": "TRK-MATCH-SECRET"})
    assert resp_status.status_code == 200
    assert b"score_breakdown" not in resp_status.data
    assert b"match_score" not in resp_status.data
    assert b"Secret Wallpaper" not in resp_status.data
