"""
FindBack 2.0 - Explainable Score Breakdown Generator

This module transforms deterministic scoring outputs into clear, human-readable
breakdowns suitable for JSON serialization and side-by-side admin review.

IMPORTANT INVARIANT:
Automated match scores and breakdowns are strictly INVESTIGATIVE LEADS for staff.
They do not constitute legal proof of device ownership.
"""

import json

def generate_breakdown(lost_report: dict, found_report: dict, score_dict: dict) -> dict:
    """
    Generate a structured, explainable breakdown dictionary suitable for
    storing as a JSON string in match_leads.score_breakdown_json.
    """
    factors = score_dict.get("factors", {})
    total_score = score_dict.get("total_score", 0)
    match_possible = score_dict.get("match_possible", False)
    summary = score_dict.get("summary", "")

    breakdown = {
        "match_possible": match_possible,
        "total_score": total_score,
        "max_score": 100,
        "summary": summary,
        "factor_points": {
            factor_name: {
                "earned": data.get("earned", 0),
                "max": data.get("max", 0),
                "matched": data.get("matched", False),
                "explanation": data.get("explanation", ""),
            }
            for factor_name, data in factors.items()
        },
        "comparison_matrix": {
            "device_type": {
                "lost": str(lost_report.get("device_type", "")),
                "found": str(found_report.get("device_type", "")),
            },
            "brand": {
                "lost": str(lost_report.get("brand", "")),
                "found": str(found_report.get("brand", "")),
            },
            "model_family": {
                "lost": str(lost_report.get("model_family", "")),
                "found": str(found_report.get("model_family", "")),
            },
            "primary_color": {
                "lost": str(lost_report.get("primary_color", "")),
                "found": str(found_report.get("primary_color", "")),
            },
            "campus_location": {
                "lost": str(lost_report.get("campus_location", "")),
                "found": str(found_report.get("campus_location", "")),
            },
            "date_discovered": {
                "lost": str(lost_report.get("date_discovered", "")),
                "found": str(found_report.get("date_discovered", "")),
            },
        },
        "investigative_disclaimer": (
            "NOTICE: This automated match score is strictly an investigative lead "
            "for human administrative review. It does not prove ownership."
        ),
    }

    return breakdown

def serialize_breakdown(breakdown_dict: dict) -> str:
    """Serialize the breakdown dictionary to a formatted JSON string."""
    return json.dumps(breakdown_dict, indent=2)

def deserialize_breakdown(json_str: str) -> dict:
    """Safely deserialize a JSON breakdown string."""
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except (ValueError, TypeError):
        return {}
