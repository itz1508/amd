"""
Patch policy for gap evaluation.
"""
from backend.phases.gap_evaluation.schema import Gap_Item


UNPATCHABLE_GAP_CODES = {
    "DER-001-NO_EVIDENCE",
    "PP-001-EMPTY_PLAN",
    "SO-001-MISSING_FIELD",
}


def can_auto_patch_gap(gap: Gap_Item) -> bool:
    """Return whether gap evaluation may synthesize an automatic package patch."""
    return gap.gap_code not in UNPATCHABLE_GAP_CODES
