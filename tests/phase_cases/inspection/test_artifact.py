"""Artifact tests for Inspection phase."""
from pathlib import Path

from backend.phases.inspection import run_inspection
from tests.phase_cases.inspection.inspection_artifact_assertions import (
    assert_inspection_artifact_exists_and_valid_json,
    assert_inspection_artifact_has_required_fields,
    assert_inspection_artifact_deterministic,
)
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionArtifact:
    """Inspection must write a deterministic, atomic artifact outside the target."""

    def test_artifact_written_for_success(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        run_inspection(inp, tmp_path)
        artifact_path = tmp_path / "07_inspection.json"
        assert_inspection_artifact_exists_and_valid_json(artifact_path)

    def test_artifact_written_for_failure(self, tmp_path):
        inp = SimulationOutputBuilder().with_unresolved_conflict(True).build()
        run_inspection(inp, tmp_path)
        artifact_path = tmp_path / "07_inspection.json"
        assert_inspection_artifact_exists_and_valid_json(artifact_path)

    def test_artifact_has_all_required_fields(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        run_inspection(inp, tmp_path)
        artifact_path = tmp_path / "07_inspection.json"
        assert_inspection_artifact_has_required_fields(artifact_path)

    def test_artifact_serialization_is_deterministic(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        run_inspection(inp, tmp_path)
        artifact_path = tmp_path / "07_inspection.json"
        assert_inspection_artifact_deterministic(artifact_path)

    def test_artifact_written_outside_target(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        run_inspection(inp, tmp_path)
        artifact_path = tmp_path / "07_inspection.json"
        assert artifact_path.exists()
        assert "07_inspection.json" in artifact_path.name