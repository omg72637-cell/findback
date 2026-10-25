"""
FindBack 2.0 - Deterministic Matching Engine

This module implements rule-based, explainable scoring between lost and found
high-value electronics reports.

CRITICAL PRIVACY & SAFETY INVARIANTS:
1. Match scores are strictly INVESTIGATIVE LEADS for campus desk staff review.
   An automated score NEVER constitutes proof of ownership.
2. Device type compatibility is a mandatory prerequisite gate. Incompatible
   device types immediately evaluate to a score of 0 and cannot produce a lead.
3. The 85-point threshold is an unvalidated design benchmark, not empirical accuracy.
4. Determinism: identical inputs must always produce the exact same numerical
   score and breakdown without variance.
"""

from datetime import datetime, date

# Provisional factor weights (DEC-12)
WEIGHT_DEVICE_TYPE = 30
WEIGHT_BRAND = 25
WEIGHT_COLOR = 15
WEIGHT_LOCATION = 15
WEIGHT_TIME_WINDOW = 15

MAX_POSSIBLE_SCORE = (
    WEIGHT_DEVICE_TYPE
    + WEIGHT_BRAND
    + WEIGHT_COLOR
    + WEIGHT_LOCATION
    + WEIGHT_TIME_WINDOW
)

# Unvalidated provisional benchmark threshold for lead generation
PROVISIONAL_LEAD_THRESHOLD = 85

# Normalized campus zone keywords for location proximity matching
CAMPUS_ZONES = (
    "library",
    "cafeteria",
    "canteen",
    "lab",
    "auditorium",
    "gym",
    "sports",
    "hostel",
    "workshop",
    "classroom",
    "hall",
)

def parse_iso_date(date_str: str):
    """Safely parse ISO date string (YYYY-MM-DD), returning date object or None."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

def compute_score(lost_report: dict, found_report: dict) -> dict:
    """
    Compute deterministic similarity score (0-100) between a lost and found report.
    
    IMPORTANT:
    This score is an INVESTIGATIVE LEAD for staff review, NEVER proof of ownership.
    """
    if not isinstance(lost_report, dict):
        lost_report = {}
    if not isinstance(found_report, dict):
        found_report = {}

    # -------------------------------------------------------------------------
    # Factor 1: Device Type Compatibility Gate (30 pts)
    # MANDATORY GATE: If device types are incompatible, comparison halts immediately.
    # -------------------------------------------------------------------------
    lost_dtype = str(lost_report.get("device_type", "")).strip().lower()
    found_dtype = str(found_report.get("device_type", "")).strip().lower()

    if not lost_dtype or not found_dtype or lost_dtype != found_dtype:
        return {
            "match_possible": False,
            "total_score": 0,
            "factors": {
                "device_type": {
                    "earned": 0,
                    "max": WEIGHT_DEVICE_TYPE,
                    "matched": False,
                    "explanation": f"Incompatible device types: '{lost_dtype or 'empty'}' vs '{found_dtype or 'empty'}'.",
                },
                "brand": {"earned": 0, "max": WEIGHT_BRAND, "matched": False, "explanation": "Skipped due to device type mismatch."},
                "color": {"earned": 0, "max": WEIGHT_COLOR, "matched": False, "explanation": "Skipped due to device type mismatch."},
                "location": {"earned": 0, "max": WEIGHT_LOCATION, "matched": False, "explanation": "Skipped due to device type mismatch."},
                "time_window": {"earned": 0, "max": WEIGHT_TIME_WINDOW, "matched": False, "explanation": "Skipped due to device type mismatch."},
            },
            "summary": "Incompatible device types: no match possible.",
        }

    factors = {
        "device_type": {
            "earned": WEIGHT_DEVICE_TYPE,
            "max": WEIGHT_DEVICE_TYPE,
            "matched": True,
            "explanation": f"Compatible device type match: '{lost_dtype}'.",
        }
    }
    total_score = WEIGHT_DEVICE_TYPE

    # -------------------------------------------------------------------------
    # Factor 2: Brand & Manufacturer Match (25 pts)
    # -------------------------------------------------------------------------
    lost_brand = str(lost_report.get("brand", "")).strip().lower()
    found_brand = str(found_report.get("brand", "")).strip().lower()
    lost_model = str(lost_report.get("model_family", "")).strip().lower()
    found_model = str(found_report.get("model_family", "")).strip().lower()

    brand_earned = 0
    brand_matched = False
    brand_explanation = "Brand did not match."

    if lost_brand and found_brand:
        if lost_brand == found_brand or lost_brand in found_brand or found_brand in lost_brand:
            brand_earned = WEIGHT_BRAND
            brand_matched = True
            brand_explanation = f"Brand match: '{lost_brand}'."
            if lost_model and found_model and (lost_model in found_model or found_model in lost_model):
                brand_explanation += f" Model family verified: '{lost_model}'."
    elif not lost_brand or not found_brand:
        brand_explanation = "Brand missing in one or both reports."

    factors["brand"] = {
        "earned": brand_earned,
        "max": WEIGHT_BRAND,
        "matched": brand_matched,
        "explanation": brand_explanation,
    }
    total_score += brand_earned

    # -------------------------------------------------------------------------
    # Factor 3: Primary Color Match (15 pts)
    # -------------------------------------------------------------------------
    lost_color = str(lost_report.get("primary_color", "")).strip().lower()
    found_color = str(found_report.get("primary_color", "")).strip().lower()

    color_earned = 0
    color_matched = False
    color_explanation = "Color did not match."

    if lost_color and found_color:
        if lost_color == found_color:
            color_earned = WEIGHT_COLOR
            color_matched = True
            color_explanation = f"Exact color match: '{lost_color}'."
        else:
            # Check for shared color token (e.g., 'midnight blue' vs 'blue')
            lost_tokens = set(lost_color.replace("-", " ").split())
            found_tokens = set(found_color.replace("-", " ").split())
            common_tokens = lost_tokens.intersection(found_tokens)
            if common_tokens:
                color_earned = WEIGHT_COLOR
                color_matched = True
                color_explanation = f"Color keyword match on: '{', '.join(sorted(common_tokens))}'."
    else:
        color_explanation = "Color missing in one or both reports."

    factors["color"] = {
        "earned": color_earned,
        "max": WEIGHT_COLOR,
        "matched": color_matched,
        "explanation": color_explanation,
    }
    total_score += color_earned

    # -------------------------------------------------------------------------
    # Factor 4: Campus Location Proximity (15 pts)
    # -------------------------------------------------------------------------
    lost_loc = str(lost_report.get("campus_location", "")).strip().lower()
    found_loc = str(found_report.get("campus_location", "")).strip().lower()

    loc_earned = 0
    loc_matched = False
    loc_explanation = "Locations appear distinct."

    if lost_loc and found_loc:
        if lost_loc == found_loc:
            loc_earned = WEIGHT_LOCATION
            loc_matched = True
            loc_explanation = f"Exact campus location match: '{lost_loc}'."
        elif lost_loc in found_loc or found_loc in lost_loc:
            loc_earned = WEIGHT_LOCATION
            loc_matched = True
            loc_explanation = f"Sub-location match: '{lost_loc}' / '{found_loc}'."
        else:
            # Check for shared campus facility / zone keyword
            shared_zones = [
                z for z in CAMPUS_ZONES if z in lost_loc and z in found_loc
            ]
            if shared_zones:
                loc_earned = WEIGHT_LOCATION
                loc_matched = True
                loc_explanation = f"Same campus zone: '{shared_zones[0].capitalize()}'."
    else:
        loc_explanation = "Location missing in one or both reports."

    factors["location"] = {
        "earned": loc_earned,
        "max": WEIGHT_LOCATION,
        "matched": loc_matched,
        "explanation": loc_explanation,
    }
    total_score += loc_earned

    # -------------------------------------------------------------------------
    # Factor 5: Time Window Plausibility (15 pts)
    # -------------------------------------------------------------------------
    lost_d = parse_iso_date(str(lost_report.get("date_discovered", "")))
    found_d = parse_iso_date(str(found_report.get("date_discovered", "")))

    time_earned = 0
    time_matched = False
    time_explanation = "Date window could not be evaluated."

    if lost_d and found_d:
        delta = (found_d - lost_d).days
        if delta < 0:
            time_earned = 0
            time_matched = False
            time_explanation = f"Inconsistent chronology: Found date ({found_d}) precedes lost date ({lost_d})."
        elif delta <= 2:
            time_earned = WEIGHT_TIME_WINDOW
            time_matched = True
            time_explanation = f"Discovered within 48 hours of report ({delta} days)."
        elif delta <= 7:
            time_earned = 10
            time_matched = True
            time_explanation = f"Discovered within 3-7 days of report ({delta} days)."
        elif delta <= 14:
            time_earned = 5
            time_matched = True
            time_explanation = f"Discovered within 8-14 days of report ({delta} days)."
        else:
            time_earned = 0
            time_matched = False
            time_explanation = f"Discovered more than 14 days after report ({delta} days)."
    else:
        time_explanation = "Date missing or malformed in reports."

    factors["time_window"] = {
        "earned": time_earned,
        "max": WEIGHT_TIME_WINDOW,
        "matched": time_matched,
        "explanation": time_explanation,
    }
    total_score += time_earned

    # Overall summary text for administrative review
    if total_score >= PROVISIONAL_LEAD_THRESHOLD:
        summary = f"High confidence lead ({total_score}/100): Matches on device type, brand, and descriptive traits. Staff review required."
    elif total_score >= 60:
        summary = f"Moderate similarity lead ({total_score}/100): Partial match on traits. Further evidence inspection recommended."
    else:
        summary = f"Low similarity ({total_score}/100): Below lead threshold."

    return {
        "match_possible": True,
        "total_score": total_score,
        "factors": factors,
        "summary": summary,
    }
