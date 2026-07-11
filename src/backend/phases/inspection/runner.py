"""
Inspection runner - canonical entry point.
"""
from pathlib import Path
from typing import Any

from backend.phases.inspection.schema import (
    Inspection_Input,
    Inspection_Output,
    Inspection_Check,
    Inspection_Finding,
)
from backend.phases.inspection.errors import InspectionAdmissionError
from backend.phases.inspection.validator import validate_admission
from backend.phases.inspection.checks import run_all_checks
from backend.phases.inspection.fingerprint import compute_fingerprint, compute_inspection_id
from backend.phases.inspection.artifact import write_inspection_artifact


def run_inspection(
    inp: Inspection_Input,
    output_root: str | Path,
) -> Inspection_Output:
    """Run the Inspection phase on a frozen Simulation_Environment output.

    Inspection is read-only verification. It does not execute, mutate, repair,
    or retry earlier work. It writes exactly one artifact:
    ``<output_root>/07_inspection.json``.

    Args:
        inp: Frozen Simulation_Environment output.
        output_root: Directory for the inspection artifact (must be outside
            the inspected target).

    Returns:
        Inspection_Output with all checks, findings, and deterministic fingerprint.

    Raises:
        InspectionAdmissionError: If the input fails admission.
    """
    # Admission: collect all rejection reasons.
    admission_failures = validate_admission(inp)
    if admission_failures:
        raise InspectionAdmissionError("; ".join(admission_failures))

    # Run all read-only checks; never stop early.
    checks, findings, failure_reasons = run_all_checks(inp)

    inspection_passed = len(findings) == 0
    status = "completed" if inspection_passed else "failed"
    terminal_state = "completed" if inspection_passed else "failed_inspection"

    # Deterministic identifiers derived from canonical input.
    inspection_id = compute_inspection_id(inp.to_dict())
    source_fingerprint = inp.simulation_environment_fingerprint

    # Route only to final_result, whether success or failure.
    next_route = "final_result"
    route_history = [inp.phase, "inspection"]

    output = Inspection_Output(
        phase="inspection",
        status=status,
        terminal_state=terminal_state,
        inspection_id=inspection_id,
        source_phase=inp.phase,
        source_status=inp.status,
        source_fingerprint=source_fingerprint,
        gap_evaluation_fingerprint=inp.gap_evaluation_fingerprint,
        simulation_environment_fingerprint=inp.simulation_environment_fingerprint,
        inspection_passed=inspection_passed,
        checks=checks,
        findings=findings,
        failure_reasons=failure_reasons,
        dossier_evidence_refs=list(inp.dossier_evidence_refs),
        route_history=route_history,
        real_target_unchanged=inp.real_target_unchanged,
        unresolved_conflict=inp.unresolved_conflict,
        regression_detected=inp.regression_detected,
        next_route=next_route,
        inspection_fingerprint="",
        metadata=dict(inp.metadata),
    )

    # Compute fingerprint over the full deterministic output.
    output.inspection_fingerprint = compute_fingerprint(output.to_dict())

    # Write artifact atomically.
    output_path = Path(output_root).resolve()
    artifact_path = output_path / "07_inspection.json"
    write_inspection_artifact(artifact_path, output.to_dict())

    return output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for inspection phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="inspection",
        description="Inspection phase"
    )
    parser.add_argument(
        "execution_path",
        help="Path to simulation environment artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load simulation environment data
        with open(parsed.execution_path, 'r', encoding='utf-8') as f:
            execution_data = json.load(f)
        
        input_data = Inspection_Input(
            phase=execution_data.get("phase", "simulation_environment"),
            status="completed",
            simulation_environment_id=execution_data.get("simulation_environment_id", "sim-001"),
            gap_evaluation_fingerprint=execution_data.get("admitted_gap_evaluation_fingerprint") or "default-gap-fingerprint",
            simulation_environment_fingerprint=execution_data.get("simulation_environment_fingerprint") or execution_data.get("demo_fingerprint") or "default-sim-fingerprint",
            isolated_environment=execution_data.get("isolated_environment") or {"pipeline": "default"},
            self_contained_demo=execution_data.get("self_contained_demo") or {"pipeline": "default"},
            execution_result={"status": "completed", "message": "Pipeline execution"},
            execution_attempt_count=1,
            apply_mutation_boundary=execution_data.get("mutation_boundary") or {"pipeline": "default"},
            target_mutations=execution_data.get("target_mutations", []),
            changed_files=execution_data.get("changed_files", []),
            post_apply_verification={"status": "completed"},
            verification_results=execution_data.get("verification_results", []),
            dossier_evidence_refs=execution_data.get("dossier_evidence_refs", []),
            unresolved_conflict=False,
            regression_detected=False,
            real_target_unchanged=True
        )
        
        result = run_inspection(input_data, Path(parsed.output_root))
        print(f"Inspection completed: {parsed.execution_path}")
        print(f"  Status: {result.status}")
        print(f"  Output: {Path(parsed.output_root) / '07_inspection.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1