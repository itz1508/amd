"""
Builder for frozen Simulation_Environment outputs used as Inspection input.
"""
from typing import Any

from backend.phases.inspection.schema import Inspection_Input


class SimulationOutputBuilder:
    """Build a canonical Simulation_Environment output for Inspection tests."""

    def __init__(self):
        self._data: dict[str, Any] = {
            "phase": "simulation_environment",
            "status": "completed",
            "simulation_environment_id": "sim-env-001",
            "gap_evaluation_fingerprint": "gap-fp-abc123",
            "simulation_environment_fingerprint": "sim-fp-def456",
            "isolated_environment": {
                "environment_id": "iso-env-001",
                "target_root": "isolated_target",
                "prepared": True,
            },
            "self_contained_demo": {
                "demo_id": "demo-001",
                "ran_successfully": True,
            },
            "execution_result": {
                "status": "success",
                "execution_id": "exec-001",
            },
            "execution_attempt_count": 1,
            "apply_mutation_boundary": {
                "boundary_root": "isolated_target",
                "boundary_enforced": True,
            },
            "target_mutations": [
                {"relative_path": "isolated_target/src/module.py", "operation": "modify"},
            ],
            "changed_files": ["isolated_target/src/module.py"],
            "post_apply_verification": {
                "status": "success",
                "verified": True,
            },
            "verification_results": [
                {"relative_path": "isolated_target/src/module.py", "status": "success"},
            ],
            "dossier_evidence_refs": [
                {"evidence_id": "dossier-001", "source_phase": "gap_evaluation"},
            ],
            "unresolved_conflict": False,
            "regression_detected": False,
            "real_target_unchanged": True,
            "next_route": "inspection",
            "metadata": {},
        }

    def with_phase(self, phase: str) -> "SimulationOutputBuilder":
        self._data["phase"] = phase
        return self

    def with_status(self, status: str) -> "SimulationOutputBuilder":
        self._data["status"] = status
        return self

    def with_simulation_environment_id(self, value: str) -> "SimulationOutputBuilder":
        self._data["simulation_environment_id"] = value
        return self

    def with_gap_evaluation_fingerprint(self, value: str | None) -> "SimulationOutputBuilder":
        self._data["gap_evaluation_fingerprint"] = value
        return self

    def with_simulation_environment_fingerprint(self, value: str | None) -> "SimulationOutputBuilder":
        self._data["simulation_environment_fingerprint"] = value
        return self

    def with_isolated_environment(self, value: dict[str, Any] | None) -> "SimulationOutputBuilder":
        self._data["isolated_environment"] = value
        return self

    def with_self_contained_demo(self, value: dict[str, Any] | None) -> "SimulationOutputBuilder":
        self._data["self_contained_demo"] = value
        return self

    def with_execution_result(self, value: dict[str, Any] | None) -> "SimulationOutputBuilder":
        self._data["execution_result"] = value
        return self

    def with_execution_attempt_count(self, value: int) -> "SimulationOutputBuilder":
        self._data["execution_attempt_count"] = value
        return self

    def with_apply_mutation_boundary(self, value: dict[str, Any] | None) -> "SimulationOutputBuilder":
        self._data["apply_mutation_boundary"] = value
        return self

    def with_target_mutations(self, value: list[dict[str, Any]]) -> "SimulationOutputBuilder":
        self._data["target_mutations"] = value
        return self

    def with_changed_files(self, value: list[str]) -> "SimulationOutputBuilder":
        self._data["changed_files"] = value
        return self

    def with_post_apply_verification(self, value: dict[str, Any] | None) -> "SimulationOutputBuilder":
        self._data["post_apply_verification"] = value
        return self

    def with_verification_results(self, value: list[dict[str, Any]]) -> "SimulationOutputBuilder":
        self._data["verification_results"] = value
        return self

    def with_dossier_evidence_refs(self, value: list[dict[str, Any]]) -> "SimulationOutputBuilder":
        self._data["dossier_evidence_refs"] = value
        return self

    def with_unresolved_conflict(self, value: bool) -> "SimulationOutputBuilder":
        self._data["unresolved_conflict"] = value
        return self

    def with_regression_detected(self, value: bool) -> "SimulationOutputBuilder":
        self._data["regression_detected"] = value
        return self

    def with_real_target_unchanged(self, value: bool) -> "SimulationOutputBuilder":
        self._data["real_target_unchanged"] = value
        return self

    def with_next_route(self, value: str | None) -> "SimulationOutputBuilder":
        self._data["next_route"] = value
        return self

    def with_metadata(self, value: dict[str, Any]) -> "SimulationOutputBuilder":
        self._data["metadata"] = value
        return self

    def build(self) -> Inspection_Input:
        return Inspection_Input(**self._data)

    def build_dict(self) -> dict[str, Any]:
        return dict(self._data)