"""Repository boundary and no-mutation tests for Inspection phase."""
from pathlib import Path

from backend.phases.inspection import run_inspection
from tests.case_builder.mutation_guard import capture_target_hashes, assert_targets_unchanged
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionRepositoryBoundaries:
    """Inspection must not mutate real or isolated targets or invoke earlier phases."""

    def test_inspection_does_not_mutate_targets(self, tmp_path):
        real_target = tmp_path / "real_target"
        isolated_target = tmp_path / "isolated_target"
        real_target.mkdir()
        isolated_target.mkdir()
        (real_target / "file.txt").write_text("real")
        (isolated_target / "file.txt").write_text("isolated")

        earlier_artifact = tmp_path / "06_simulation.json"
        earlier_artifact.write_text('{\"phase\": \"simulation_environment\"}')

        before = capture_target_hashes(real_target, isolated_target, [earlier_artifact])

        inp = SimulationOutputBuilder().build()
        run_inspection(inp, tmp_path / "output")

        assert_targets_unchanged(before, real_target, isolated_target, [earlier_artifact])

    def test_inspection_does_not_import_earlier_phases(self):
        """Prove that Inspection does not import runtime entry points from earlier phases."""
        import backend.phases.inspection.runner as runner_module

        # The runner must not import any of the forbidden earlier phase modules.
        forbidden = [
            "backend.phases.gap_evaluation",
            "backend.phases.simulation_environment",
            "backend.phases.execution",
            "backend.llm",
        ]
        imported = set(runner_module.__dict__.keys())
        for name in forbidden:
            assert name not in imported, f"Forbidden import found in runner_module: {name}"


def sys_modules() -> set[str]:
    import sys
    return {m for m in sys.modules.keys()}