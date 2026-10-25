"""
FindBack 2.0 - Deterministic Matching Package

Exports deterministic scoring, explanation breakdown utilities, and dispute management.
"""

from matching.matcher import (
    compute_score,
    PROVISIONAL_LEAD_THRESHOLD,
    WEIGHT_DEVICE_TYPE,
    WEIGHT_BRAND,
    WEIGHT_COLOR,
    WEIGHT_LOCATION,
    WEIGHT_TIME_WINDOW,
)
from matching.explainer import (
    generate_breakdown,
    serialize_breakdown,
    deserialize_breakdown,
)
from matching.service import (
    find_and_record_matches,
    can_lead_proceed_to_handover,
)

__all__ = [
    "compute_score",
    "PROVISIONAL_LEAD_THRESHOLD",
    "WEIGHT_DEVICE_TYPE",
    "WEIGHT_BRAND",
    "WEIGHT_COLOR",
    "WEIGHT_LOCATION",
    "WEIGHT_TIME_WINDOW",
    "generate_breakdown",
    "serialize_breakdown",
    "deserialize_breakdown",
    "find_and_record_matches",
    "can_lead_proceed_to_handover",
]
