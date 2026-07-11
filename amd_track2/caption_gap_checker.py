"""Agent B validation: check captions against extracted context."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amd_track2.caption_writer import _TECH_JARGON_TERMS
from amd_track2.context_extractor import ContextResult

logger = logging.getLogger(__name__)


# Gap codes as specified in the implementation plan
GAP_CODES = {
    "MISSING_STYLE": "CAP-001-MISSING-STYLE",
    "EMPTY_CAPTION": "CAP-002-EMPTY-CAPTION",
    "TECH_JARGON": "CAP-003-TECH-JARGON",
    "IDENTICAL_CAPTIONS": "CAP-004-IDENTICAL-CAPTIONS",
    "NOT_GROUNDED": "CAP-005-NOT-GROUNDED",
    "CONTRADICTION": "CAP-006-CONTRADICTION",
    "FORMAL_MISMATCH": "CAP-007-FORMAL-MISMATCH",
    "SARCASTIC_MISMATCH": "CAP-008-SARCASTIC-MISMATCH",
    "TECH_HUMOR_MISSING": "CAP-009-TECH-HUMOR-MISSING",
    "NONTECH_HUMOR_MISSING": "CAP-010-NONTECH-HUMOR-MISSING",
}


@dataclass
class Gap:
    """A single validation gap with structured issue code."""

    style: str
    gap_code: str
    evidence: str
    required_fix: str
    severity: str = "medium"


@dataclass
class GapReport:
    """Result of caption validation."""

    valid: bool
    gaps: List[Gap]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "gaps": [
                {
                    "style": g.style,
                    "code": g.gap_code,
                    "severity": g.severity,
                    "description": g.evidence,
                    "repair_hint": g.required_fix,
                }
                for g in self.gaps
            ],
        }


class CaptionGapChecker:
    """Validate Agent A captions against Agent B context."""

    def __init__(self):
        self.tech_jargon = set(t.lower() for t in _TECH_JARGON_TERMS)

    def check(
        self,
        captions: Dict[str, str],
        context: ContextResult,
        requested_styles: List[str],
    ) -> GapReport:
        """Run all validation checks and return a gap report."""
        gaps: List[Gap] = []

        # Schema completeness
        for style in requested_styles:
            if style not in captions:
                gaps.append(
                    Gap(
                        style=style,
                        gap_code=GAP_CODES["MISSING_STYLE"],
                        evidence=f"style '{style}' not in output",
                        required_fix=f"add caption for style '{style}'",
                        severity="high",
                    )
                )
            else:
                val = captions[style]
                if not isinstance(val, str) or not val.strip():
                    gaps.append(
                        Gap(
                            style=style,
                            gap_code=GAP_CODES["EMPTY_CAPTION"],
                            evidence=f"style '{style}' is empty or not a string",
                            required_fix=f"write non-empty string for style '{style}'",
                            severity="high",
                        )
                    )

        # Check for tech jargon in humorous_non_tech
        if "humorous_non_tech" in captions:
            non_tech = captions["humorous_non_tech"].lower()
            found_jargon = [t for t in self.tech_jargon if t in non_tech]
            if found_jargon:
                gaps.append(
                    Gap(
                        style="humorous_non_tech",
                        gap_code=GAP_CODES["TECH_JARGON"],
                        evidence=f"caption contains tech terms: {found_jargon[:5]}",
                        required_fix="rewrite with everyday humor, no tech jargon",
                        severity="medium",
                    )
                )

        # Check captions are not identical across styles
        values = [v.strip().lower() for v in captions.values() if isinstance(v, str)]
        if len(values) > 1 and len(set(values)) == 1:
            gaps.append(
                Gap(
                    style="all",
                    gap_code=GAP_CODES["IDENTICAL_CAPTIONS"],
                    evidence="all captions are identical",
                    required_fix="make each style meaningfully different",
                    severity="high",
                )
            )

        # Grounding check: caption should mention something from context
        context_text = " ".join(
            [
                context.scene_summary.lower(),
                " ".join(s.lower() for s in context.main_subjects),
                " ".join(a.lower() for a in context.actions),
                " ".join(o.lower() for o in context.important_objects),
            ]
        )
        for style, caption in captions.items():
            if not isinstance(caption, str):
                continue
            cap_lower = caption.lower()
            # Simple heuristic: at least one word from context should appear
            context_words = set(w for w in context_text.split() if len(w) > 3)
            if context_words and not any(w in cap_lower for w in context_words):
                gaps.append(
                    Gap(
                        style=style,
                        gap_code=GAP_CODES["NOT_GROUNDED"],
                        evidence="caption does not reference visible scene elements",
                        required_fix="rewrite caption to mention visible subjects/actions",
                        severity="high",
                    )
                )

        # Check for contradictions with must_not_claim
        for style, caption in captions.items():
            if not isinstance(caption, str):
                continue
            cap_lower = caption.lower()
            for claim in context.must_not_claim:
                if claim.lower() in cap_lower:
                    gaps.append(
                        Gap(
                            style=style,
                            gap_code=GAP_CODES["CONTRADICTION"],
                            evidence=f"caption contradicts must_not_claim: '{claim}'",
                            required_fix="remove or rephrase the contradictory claim",
                            severity="high",
                        )
                    )

        valid = len(gaps) == 0
        if not valid:
            logger.warning("Gap checker found %d issues", len(gaps))
        return GapReport(valid=valid, gaps=gaps)