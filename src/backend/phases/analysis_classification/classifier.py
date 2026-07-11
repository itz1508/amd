"""
Request and source item classifier.

Determines request_kind and produces exactly one Classification_Decision
per Analysis_Item without mutating anything.
"""
import hashlib
import json
from typing import Any

from backend.phases.analysis_classification.schema import (
    Analysis_Item,
    Classification_Decision,
    Classification_Notice,
)


REQUEST_KIND_KEYWORDS: dict[str, list[str]] = {
    "diagnostic": [
        "diagnose", "diagnostic", "inspect", "inspect", "identify", "compare",
        "explain", "what is", "what are", "how does", "why does", "analyze",
        "analyse", "investigate", "debug", "trace", "profile", "assess",
    ],
    "additive": [
        "add", "implement", "create", "introduce", "new feature", "support",
        "enable", "provide", "build", "extend", "expand", "enhance", "missing",
    ],
    "corrective": [
        "fix", "repair", "correct", "resolve", "bug", "defect", "broken",
        "error", "issue", "problem", "fail", "failure", "crash", "wrong",
    ],
    "migration": [
        "migrate", "migration", "move", "port", "convert", "upgrade", "transition",
        "rewrite", "replace", "rebuild",
    ],
    "verification": [
        "verify", "validate", "check", "confirm", "ensure", "test", "prove",
        "certify", "audit",
    ],
    "informational": [
        "document", "describe", "summarize", "summary", "overview", "information",
        "inform", "report", "list", "enumerate",
    ],
}


ALLOWED_ACTIONS: dict[str, list[str]] = {
    "fix": ["fix"],
    "upgrade": ["upgrade"],
    "rebuild": ["rebuild"],
    "replace": ["replace"],
    "no_change": ["no_change"],
    "needs_review": ["fix", "upgrade", "rebuild", "replace", "no_change", "needs_review"],
}


def classify_request_kind(request_text: str) -> str:
    """Classify the original request into a request_kind.

    Args:
        request_text: The original request text.

    Returns:
        One of the canonical request_kind values.
    """
    text_lower = request_text.lower()
    scores: dict[str, int] = {kind: 0 for kind in REQUEST_KIND_KEYWORDS}

    for kind, keywords in REQUEST_KIND_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                scores[kind] += 1

    # Explicit diagnostic/verification intent takes precedence over generic
    # corrective keywords that may appear inside the explanation.
    if scores["diagnostic"] > 0 and any(
        word in text_lower for word in ["diagnose", "diagnostic", "why", "explain", "analyze", "analyse", "investigate", "debug"]
    ):
        return "diagnostic"

    if scores["verification"] > 0 and any(
        word in text_lower for word in ["verify", "validate", "confirm", "ensure", "prove", "certify", "audit"]
    ):
        return "verification"

    # Migration and corrective often overlap; prefer migration only when explicit.
    if scores["migration"] > 0 and ("migrate" in text_lower or "migration" in text_lower or "port" in text_lower):
        return "migration"

    # Corrective only if clear defect language.
    if scores["corrective"] > 0 and any(word in text_lower for word in ["fix", "bug", "defect", "broken", "error", "fail", "crash"]):
        return "corrective"

    # Additive when new capability is requested.
    if scores["additive"] > 0:
        return "additive"

    # Diagnostic when inspecting/explaining existing behavior.
    if scores["diagnostic"] > 0:
        return "diagnostic"

    if scores["verification"] > 0:
        return "verification"

    if scores["informational"] > 0:
        return "informational"

    return "unknown"


def _derive_classification_id(source_item_id: str, request_kind: str, category: str) -> str:
    payload = {
        "source_item_id": source_item_id,
        "request_kind": request_kind,
        "category": category,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"cls:{digest[:16]}"


def _classify_file(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    payload = item.source_payload
    file_type = payload.get("file_type")
    category = payload.get("category")
    language = payload.get("language")

    if file_type == "build":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "maintainability"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="maintainability",
            actionable=False,
            severity="informational",
            confidence=0.7,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Build artifact is not a source responsibility.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    if file_type == "config":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "configuration"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="configuration",
            actionable=False,
            severity="informational",
            confidence=0.75,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Configuration file; no action unless request specifically targets it.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    if file_type == "test":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "test_gap"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="test_gap",
            actionable=False,
            severity="informational",
            confidence=0.6,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Test file; may indicate coverage gap depending on request scope.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    if file_type == "source":
        if category == "package":
            return Classification_Decision(
                classification_id=_derive_classification_id(item.source_item_id, request_kind, "maintainability"),
                source_item_id=item.source_item_id,
                request_kind=request_kind,
                classification_category="maintainability",
                actionable=False,
                severity="informational",
                confidence=0.65,
                recommended_action="no_change",
                allowed_actions=ALLOWED_ACTIONS["no_change"],
                rationale="Package marker file; structural boundary only.",
                evidence_refs=item.source_evidence_refs,
                affected_paths=[item.source_path] if item.source_path else [],
            )

        if language is None:
            return Classification_Decision(
                classification_id=_derive_classification_id(item.source_item_id, request_kind, "unsupported"),
                source_item_id=item.source_item_id,
                request_kind=request_kind,
                classification_category="unsupported",
                actionable=True,
                severity="minor",
                confidence=0.5,
                recommended_action="needs_review",
                allowed_actions=ALLOWED_ACTIONS["needs_review"],
                rationale="Source file with unsupported or unknown language.",
                evidence_refs=item.source_evidence_refs,
                affected_paths=[item.source_path] if item.source_path else [],
            )

        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "maintainability"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="maintainability",
            actionable=False,
            severity="informational",
            confidence=0.6,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Source file within scope; no specific defect detected.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    if file_type == "data":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "informational"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="informational",
            actionable=False,
            severity="informational",
            confidence=0.7,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Data file; not actionable without explicit request.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, "unknown"),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category="unknown",
        actionable=True,
        severity="minor",
        confidence=0.5,
        recommended_action="needs_review",
        allowed_actions=ALLOWED_ACTIONS["needs_review"],
        rationale="File type could not be confidently classified.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
    )


def _classify_surface(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    payload = item.source_payload
    surface_type = payload.get("surface_type")

    if surface_type == "entry_point":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "interface_drift"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="interface_drift",
            actionable=False,
            severity="informational",
            confidence=0.6,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Entry point surface detected; no drift evidence present.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    if surface_type == "build_config":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "configuration"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="configuration",
            actionable=False,
            severity="informational",
            confidence=0.7,
            recommended_action="no_change",
            allowed_actions=ALLOWED_ACTIONS["no_change"],
            rationale="Build configuration surface.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
        )

    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, "informational"),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category="informational",
        actionable=False,
        severity="informational",
        confidence=0.6,
        recommended_action="no_change",
        allowed_actions=ALLOWED_ACTIONS["no_change"],
        rationale="Repository surface detected.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
    )


def _classify_notice(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    payload = item.source_payload
    notice_code = payload.get("notice_code")

    if notice_code == "unreadable":
        return Classification_Decision(
            classification_id=_derive_classification_id(item.source_item_id, request_kind, "unreadable"),
            source_item_id=item.source_item_id,
            request_kind=request_kind,
            classification_category="unreadable",
            actionable=True,
            severity="minor",
            confidence=0.8,
            recommended_action="needs_review",
            allowed_actions=ALLOWED_ACTIONS["needs_review"],
            rationale="Scan could not read the file; requires review.",
            evidence_refs=item.source_evidence_refs,
            affected_paths=[item.source_path] if item.source_path else [],
            failure_reasons=["scan_unreadable"],
        )

    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, "informational"),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category="informational",
        actionable=False,
        severity="informational",
        confidence=0.7,
        recommended_action="no_change",
        allowed_actions=ALLOWED_ACTIONS["no_change"],
        rationale="Scan notice; informational unless request targets it.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
    )


def _classify_duplicate_group(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, "duplication"),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category="duplication",
        actionable=True,
        severity="major",
        confidence=0.75,
        recommended_action="needs_review",
        allowed_actions=ALLOWED_ACTIONS["needs_review"],
        rationale="Duplicate implementation evidence detected; canonical selection deferred.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
        duplicate_group_id=item.source_item_id,
    )


def _classify_drift_record(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    payload = item.source_payload
    drift_type = payload.get("drift_type", "artifact_drift")
    category = drift_type if drift_type in {
        "interface_drift", "behavior_drift", "import_drift", "artifact_drift"
    } else "artifact_drift"

    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, category),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category=category,
        actionable=True,
        severity="major",
        confidence=0.7,
        recommended_action="needs_review",
        allowed_actions=ALLOWED_ACTIONS["needs_review"],
        rationale=f"Drift evidence detected: {drift_type}; resolution deferred.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
        drift_detected=True,
    )


def _classify_unsupported_or_unknown(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    return Classification_Decision(
        classification_id=_derive_classification_id(item.source_item_id, request_kind, "unsupported"),
        source_item_id=item.source_item_id,
        request_kind=request_kind,
        classification_category="unsupported",
        actionable=True,
        severity="minor",
        confidence=0.5,
        recommended_action="needs_review",
        allowed_actions=ALLOWED_ACTIONS["needs_review"],
        rationale="Incomplete, unsupported, or unknown source record; requires review.",
        evidence_refs=item.source_evidence_refs,
        affected_paths=[item.source_path] if item.source_path else [],
        failure_reasons=["incomplete_or_unsupported_record"],
    )


def classify_item(item: Analysis_Item, request_kind: str) -> Classification_Decision:
    """Return exactly one Classification_Decision for an Analysis_Item.

    Args:
        item: Normalized Analysis_Item.
        request_kind: Classified request kind.

    Returns:
        Classification_Decision.
    """
    if item.source_kind == "file":
        return _classify_file(item, request_kind)
    if item.source_kind == "surface":
        return _classify_surface(item, request_kind)
    if item.source_kind == "notice":
        return _classify_notice(item, request_kind)
    if item.source_kind == "duplicate_group":
        return _classify_duplicate_group(item, request_kind)
    if item.source_kind == "drift_record":
        return _classify_drift_record(item, request_kind)

    return _classify_unsupported_or_unknown(item, request_kind)


def classify_items(
    items: list[Analysis_Item],
    request_kind: str,
) -> tuple[list[Classification_Decision], list[Classification_Notice]]:
    """Classify all items and emit any notices.

    Args:
        items: Normalized Analysis_Items.
        request_kind: Classified request kind.

    Returns:
        Tuple of (decisions, notices).
    """
    decisions: list[Classification_Decision] = []
    notices: list[Classification_Notice] = []

    for item in items:
        decision = classify_item(item, request_kind)
        decisions.append(decision)

    # Sort decisions deterministically
    decisions.sort(key=lambda d: (d.source_item_id, d.classification_id))

    return decisions, notices