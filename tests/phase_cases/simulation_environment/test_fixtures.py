"""Test fixtures for Simulation Environment tests."""
import tempfile
from pathlib import Path
from src.backend.phases.simulation_environment.schema import (
    Simulation_Environment_Input,
    Simulation_Environment_Output,
)


def make_valid_gap_evaluation_output(
    readiness=1.0,
    simulation_ready=True,
    required_grader_failures=None,
    unresolved_conflict=False,
    next_route="simulation_environment",
    resulting_package_plan=None,
):
    """Create a valid Gap_Evaluation_Output for testing."""
    if required_grader_failures is None:
        required_grader_failures = []
    if resulting_package_plan is None:
        resulting_package_plan = {"name": "test-pkg", "version": "1.0.0"}
    
    # Compute fingerprint for the resulting package plan
    import hashlib, json
    def normalize_value(v):
        if isinstance(v, dict):
            return {k: normalize_value(val) for k, val in sorted(v.items())}
        elif isinstance(v, list):
            return sorted(normalize_value(item) for item in v)
        elif isinstance(v, (str, int, float, bool)):
            return v
        elif v is None:
            return None
        else:
            return str(v)
    
    normalized = normalize_value(resulting_package_plan)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    resulting_fp = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    
    return {
        "phase": "gap_evaluation",
        "status": "completed",
        "readiness": readiness,
        "simulation_ready": simulation_ready,
        "required_grader_failures": list(required_grader_failures),
        "unresolved_conflict": unresolved_conflict,
        "attempts": [],
        "gaps": [],
        "applied_package_plan_patches": [],
        "resulting_package_plan": resulting_package_plan,
        "resulting_package_plan_fingerprint": resulting_fp,
        "supporting_metadata": {},
        "dossier_evidence_refs": ["der-001"],
        "next_route": next_route,
        "handoff_ref": None,
        "gap_evaluation_fingerprint": "gap-eval-fp-001",
    }


def make_valid_package_plan():
    """Create a valid package plan for testing."""
    return {
        "name": "test-pkg",
        "version": "1.0.0",
    }


def make_valid_input(
    gap_eval=None,
    package_plan=None,
    supporting_metadata=None,
    dossier_refs=None,
    isolated_location="",
):
    """Create a valid Simulation_Environment_Input for testing."""
    if gap_eval is None:
        gap_eval = make_valid_gap_evaluation_output()
    if package_plan is None:
        package_plan = make_valid_package_plan()
    if supporting_metadata is None:
        supporting_metadata = {}
    if dossier_refs is None:
        dossier_refs = ["der-001"]
    
    return Simulation_Environment_Input(
        gap_evaluation_output=gap_eval,
        admitted_package_plan=package_plan,
        supporting_metadata=supporting_metadata,
        dossier_evidence_refs=dossier_refs,
        isolated_output_location=isolated_location,
    )


def make_invalid_input_below_threshold():
    """Create input with readiness below threshold."""
    return make_valid_input(
        gap_eval=make_valid_gap_evaluation_output(readiness=0.9390)
    )


def make_invalid_input_not_simulation_ready():
    """Create input where simulation_ready is false."""
    return make_valid_input(
        gap_eval=make_valid_gap_evaluation_output(simulation_ready=False)
    )


def make_invalid_input_with_grader_failures():
    """Create input with required grader failures."""
    return make_valid_input(
        gap_eval=make_valid_gap_evaluation_output(
            required_grader_failures=["error-001"]
        )
    )


def make_invalid_input_with_conflict():
    """Create input with unresolved conflict."""
    return make_valid_input(
        gap_eval=make_valid_gap_evaluation_output(
            unresolved_conflict=True
        )
    )


def make_invalid_input_wrong_route():
    """Create input with wrong next_route."""
    return make_valid_input(
        gap_eval=make_valid_gap_evaluation_output(
            next_route="gap_handoff"
        )
    )


# Test data for isolated environment

def create_test_target_structure(tmpdir):
    """Create a test target structure for testing."""
    target_dir = Path(tmpdir) / "test_target"
    target_dir.mkdir()
    
    # Create some test files
    (target_dir / "main.py").write_text("print('Hello, world!')")
    (target_dir / "utils.py").write_text("def helper(): pass")
    (target_dir / "config.json").write_text('{"name": "test"}')
    
    return str(target_dir)


def create_temp_isolated_location(tmpdir):
    """Create a temporary isolated location."""
    isolated_dir = Path(tmpdir) / "isolated_env"
    isolated_dir.mkdir()
    return str(isolated_dir)
