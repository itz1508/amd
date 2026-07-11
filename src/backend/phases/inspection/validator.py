"""
Inspection admission validator.
"""
from backend.phases.inspection.schema import Inspection_Input
from backend.phases.inspection.errors import InspectionAdmissionError


def validate_admission(inp: Inspection_Input) -> list[str]:
    """Validate that the Simulation_Environment output may enter Inspection.

    Returns a list of admission failure reasons. An empty list means admission
    is granted. Inspection does not stop at the first failure; all rejection
    reasons are collected.
    """
    failures: list[str] = []

    if inp.phase != "simulation_environment":
        failures.append(
            f"Admission rejected: expected phase 'simulation_environment', got '{inp.phase}'"
        )

    if inp.status != "completed":
        failures.append(
            f"Admission rejected: Simulation_Environment status must be 'completed', got '{inp.status}'"
        )

    if not inp.simulation_environment_fingerprint:
        failures.append("Admission rejected: simulation_environment_fingerprint is missing")

    if not inp.gap_evaluation_fingerprint:
        failures.append("Admission rejected: gap_evaluation_fingerprint is missing")

    if not inp.execution_result:
        failures.append("Admission rejected: execution evidence is missing")

    if inp.execution_attempt_count != 1:
        failures.append(
            f"Admission rejected: execution_attempt_count must be exactly 1, got {inp.execution_attempt_count}"
        )

    if not inp.isolated_environment:
        failures.append("Admission rejected: isolated_environment evidence is missing")

    if not inp.self_contained_demo:
        failures.append("Admission rejected: self_contained_demo evidence is missing")

    if not inp.apply_mutation_boundary:
        failures.append("Admission rejected: apply_mutation_boundary evidence is missing")

    if not inp.post_apply_verification:
        failures.append("Admission rejected: post_apply_verification evidence is missing")

    if not _dossier_refs_well_formed(inp.dossier_evidence_refs):
        failures.append("Admission rejected: dossier_evidence_refs are malformed")

    if not inp.real_target_unchanged:
        failures.append("Admission rejected: input claims the real target changed")

    return failures


def _dossier_refs_well_formed(refs: list[dict]) -> bool:
    """Return True if every dossier evidence reference has the required shape."""
    if not isinstance(refs, list):
        return False
    for ref in refs:
        if not isinstance(ref, dict):
            return False
        if "evidence_id" not in ref or not ref["evidence_id"]:
            return False
        if "source_phase" not in ref or not ref["source_phase"]:
            return False
    return True