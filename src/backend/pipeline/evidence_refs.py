"""
Evidence reference adapters for cross-phase pipeline boundaries.
"""
from pathlib import Path
from typing import Any


PHASE_BY_ARTIFACT_NAME = {
    "01_snapshot.json": "snapshot",
    "02_scan.json": "scan",
    "03_analysis_classification.json": "analysis_classification",
    "04_statement_output.json": "statement_output",
    "05_gap_evaluation.json": "gap_evaluation",
    "06_final_handoff.json": "final_handoff",
    "06_simulation_environment.json": "simulation_environment",
    "07_inspection.json": "inspection",
    "08_final_result.json": "final_result",
}


def to_inspection_evidence_refs(refs: list[Any]) -> list[dict[str, Any]]:
    """Convert dossier refs into Inspection evidence record shape."""
    records: list[dict[str, Any]] = []
    for index, ref in enumerate(refs, start=1):
        if isinstance(ref, dict):
            evidence_id = ref.get("evidence_id") or ref.get("path") or ref.get("ref")
            source_phase = ref.get("source_phase")
            payload_summary = ref.get("payload_summary", {})
        else:
            path = Path(str(ref))
            evidence_id = str(ref)
            source_phase = PHASE_BY_ARTIFACT_NAME.get(path.name, "dossier")
            payload_summary = {"path": str(ref), "ordinal": index}

        if evidence_id and source_phase:
            records.append({
                "evidence_id": evidence_id,
                "source_phase": source_phase,
                "evidence_type": "dossier",
                "payload_summary": payload_summary,
            })
    return records


def to_string_evidence_refs(refs: list[Any]) -> list[str]:
    """Convert dossier refs into Final_Result string reference shape."""
    values: list[str] = []
    for ref in refs:
        if isinstance(ref, dict):
            evidence_id = ref.get("evidence_id") or ref.get("path") or ref.get("ref")
            if evidence_id:
                values.append(str(evidence_id))
        elif ref:
            values.append(str(ref))
    return values
