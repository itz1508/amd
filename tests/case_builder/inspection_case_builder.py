"""
Helpers for constructing common Inspection test cases.
"""
from typing import Any

from backend.phases.inspection.schema import Inspection_Input
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


def valid_simulation_output() -> Inspection_Input:
    """Return a fully valid Simulation_Environment output."""
    return SimulationOutputBuilder().build()


def admission_rejected_cases() -> list[tuple[str, Inspection_Input, str]]:
    """Return cases that should be rejected at admission."""
    return [
        (
            "wrong phase",
            SimulationOutputBuilder().with_phase("gap_evaluation").build(),
            "simulation_environment",
        ),
        (
            "failed status",
            SimulationOutputBuilder().with_status("failed").build(),
            "completed",
        ),
        (
            "missing simulation fingerprint",
            SimulationOutputBuilder().with_simulation_environment_fingerprint("").build(),
            "simulation_environment_fingerprint",
        ),
        (
            "missing gap fingerprint",
            SimulationOutputBuilder().with_gap_evaluation_fingerprint("").build(),
            "gap_evaluation_fingerprint",
        ),
        (
            "missing execution evidence",
            SimulationOutputBuilder().with_execution_result({}).build(),
            "execution evidence",
        ),
        (
            "zero execution attempts",
            SimulationOutputBuilder().with_execution_attempt_count(0).build(),
            "exactly 1",
        ),
        (
            "multiple execution attempts",
            SimulationOutputBuilder().with_execution_attempt_count(2).build(),
            "exactly 1",
        ),
        (
            "missing isolated environment",
            SimulationOutputBuilder().with_isolated_environment({}).build(),
            "isolated_environment",
        ),
        (
            "missing self-contained demo",
            SimulationOutputBuilder().with_self_contained_demo({}).build(),
            "self_contained_demo",
        ),
        (
            "missing mutation boundary",
            SimulationOutputBuilder().with_apply_mutation_boundary({}).build(),
            "apply_mutation_boundary",
        ),
        (
            "missing post-apply verification",
            SimulationOutputBuilder().with_post_apply_verification({}).build(),
            "post_apply_verification",
        ),
        (
            "malformed dossier refs",
            SimulationOutputBuilder().with_dossier_evidence_refs([{"bad": "ref"}]).build(),
            "dossier_evidence_refs",
        ),
        (
            "real target changed",
            SimulationOutputBuilder().with_real_target_unchanged(False).build(),
            "real target changed",
        ),
    ]


def failed_check_cases() -> list[tuple[str, Inspection_Input, list[str]]]:
    """Return cases that pass admission but fail specific checks.

    These cases use *present-but-invalid* evidence so admission (which rejects
    missing/empty structural fields) does not short-circuit before the checks run.
    """
    return [
        (
            "invalid self-contained demo evidence",
            SimulationOutputBuilder().with_self_contained_demo({"ran_successfully": False}).build(),
            ["F-SE06"],
        ),
        (
            "invalid execution evidence",
            SimulationOutputBuilder().with_execution_result({"status": "failure", "execution_id": "exec-bad"}).build(),
            ["F-SE08"],
        ),
        (
            "invalid mutation boundary evidence",
            SimulationOutputBuilder()
            .with_apply_mutation_boundary({"boundary_root": ""})
            .build(),
            ["F-SE09", "F-SE10", "F-SE11"],
        ),
        (
            "changed file outside isolated target",
            SimulationOutputBuilder()
            .with_changed_files(["real_target/src/module.py"])
            .with_target_mutations([{"relative_path": "real_target/src/module.py", "operation": "modify"}])
            .with_verification_results([{"relative_path": "real_target/src/module.py", "status": "success"}])
            .build(),
            ["F-SE10", "F-SE11"],
        ),
        (
            "changed-files and target-mutation mismatch",
            SimulationOutputBuilder()
            .with_changed_files(["isolated_target/src/other.py"])
            .build(),
            ["F-SE12"],
        ),
        (
            "invalid post-apply verification",
            SimulationOutputBuilder().with_post_apply_verification({"status": "failure", "verified": False}).build(),
            ["F-SE14"],
        ),
        (
            "incomplete changed-file verification",
            SimulationOutputBuilder()
            .with_changed_files(["isolated_target/src/a.py", "isolated_target/src/b.py"])
            .with_target_mutations([
                {"relative_path": "isolated_target/src/a.py", "operation": "modify"},
                {"relative_path": "isolated_target/src/b.py", "operation": "modify"},
            ])
            .with_verification_results([{"relative_path": "isolated_target/src/a.py", "status": "success"}])
            .build(),
            ["F-SE13"],
        ),
        (
            "failed post-apply verification",
            SimulationOutputBuilder()
            .with_post_apply_verification({"status": "failure", "verified": False})
            .with_verification_results([{"relative_path": "isolated_target/src/module.py", "status": "failure"}])
            .build(),
            ["F-SE14"],
        ),
    ]
