"""
Helpers for constructing common Analysis_Classification test cases.
"""
from typing import Any

from backend.phases.analysis_classification.schema import Analysis_Classification_Input
from backend.schemas.scan import Scan_Output
from tests.case_builder.scan_output_builder import ScanOutputBuilder


def valid_analysis_classification_input() -> Analysis_Classification_Input:
    """Return a fully valid Analysis_Classification input."""
    return (
        Analysis_ClassificationInputBuilder()
        .with_request_text("Fix the bug in module.py")
        .build()
    )


def admission_rejected_cases() -> list[tuple[str, Analysis_Classification_Input | dict[str, Any], str]]:
    """Return cases that should be rejected at admission."""
    return [
        (
            "missing request_id",
            Analysis_ClassificationInputBuilder().with_request_id("").build(),
            "request_id is missing or empty",
        ),
        (
            "missing request_text",
            Analysis_ClassificationInputBuilder().with_request_text("").build(),
            "request_text is missing or not a non-empty string",
        ),
        (
            "missing scan_output",
            Analysis_ClassificationInputBuilder().with_scan_output(None).build_dict(),
            "scan_output is missing",
        ),
        (
            "wrong scan phase",
            Analysis_ClassificationInputBuilder()
            .with_scan_output(ScanOutputBuilder().with_phase("analysis_classification").build())
            .build(),
            "scan_output.phase must be 'scan'",
        ),
        (
            "scan not completed",
            Analysis_ClassificationInputBuilder()
            .with_scan_output(ScanOutputBuilder().with_status("failed").build())
            .build(),
            "scan_output.status must be 'completed'",
        ),
        (
            "missing snapshot fingerprint",
            Analysis_ClassificationInputBuilder()
            .with_scan_output(ScanOutputBuilder().with_snapshot_fingerprint("").build())
            .build(),
            "snapshot_fingerprint is missing or empty",
        ),
        (
            "missing scan fingerprint",
            Analysis_ClassificationInputBuilder()
            .with_scan_output(ScanOutputBuilder().with_scan_fingerprint("").build())
            .build(),
            "scan_fingerprint is missing or empty",
        ),
        (
            "missing target_root",
            Analysis_ClassificationInputBuilder()
            .with_scan_output(ScanOutputBuilder().with_target_root("").build())
            .build(),
            "target_root is missing or empty",
        ),
        (
            "malformed dossier refs",
            Analysis_ClassificationInputBuilder().with_dossier_evidence_refs([{"bad": "ref"}]).build(),
            "dossier_evidence_refs must be a list of non-empty strings",
        ),
    ]


class Analysis_ClassificationInputBuilder:
    """Build a canonical Analysis_Classification_Input."""

    def __init__(self):
        self._data: dict[str, Any] = {
            "request_id": "req-001",
            "request_text": "Fix the bug in module.py",
            "scan_output": ScanOutputBuilder().build(),
            "request_metadata": {"origin": "test"},
            "dossier_evidence_refs": ["dossier-001"],
            "metadata": {},
        }

    def with_request_id(self, value: str) -> "Analysis_ClassificationInputBuilder":
        self._data["request_id"] = value
        return self

    def with_request_text(self, value: str) -> "Analysis_ClassificationInputBuilder":
        self._data["request_text"] = value
        return self

    def with_scan_output(self, value: Scan_Output | dict[str, Any] | None) -> "Analysis_ClassificationInputBuilder":
        self._data["scan_output"] = value
        return self

    def with_request_metadata(self, value: dict[str, Any]) -> "Analysis_ClassificationInputBuilder":
        self._data["request_metadata"] = value
        return self

    def with_dossier_evidence_refs(self, value: list[str] | list[dict[str, Any]]) -> "Analysis_ClassificationInputBuilder":
        self._data["dossier_evidence_refs"] = value
        return self

    def with_metadata(self, value: dict[str, Any]) -> "Analysis_ClassificationInputBuilder":
        self._data["metadata"] = value
        return self

    def with_duplicate_groups(self, value: list[dict[str, Any]]) -> "Analysis_ClassificationInputBuilder":
        ext = self._data.setdefault("metadata", {})
        ext.setdefault("analysis_classification_extensions", {})
        ext["analysis_classification_extensions"]["duplicate_groups"] = value
        return self

    def with_drift_records(self, value: list[dict[str, Any]]) -> "Analysis_ClassificationInputBuilder":
        ext = self._data.setdefault("metadata", {})
        ext.setdefault("analysis_classification_extensions", {})
        ext["analysis_classification_extensions"]["drift_records"] = value
        return self

    def build(self) -> Analysis_Classification_Input:
        return Analysis_Classification_Input(**self._data)

    def build_dict(self) -> dict[str, Any]:
        return {
            **self._data,
            "scan_output": (
                self._data["scan_output"].to_dict()
                if hasattr(self._data["scan_output"], "to_dict")
                else self._data["scan_output"]
            ),
        }