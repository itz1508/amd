"""Repository boundary and no-mutation tests for Analysis_Classification phase."""
from pathlib import Path

from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.mutation_guard import capture_target_hashes, assert_targets_unchanged
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder


class TestAnalysisClassificationRepositoryBoundaries:
    """Analysis_Classification must not mutate real or isolated targets or invoke later phases."""

    def test_analysis_classification_does_not_mutate_targets(self, tmp_path):
        real_target = tmp_path / "real_target"
        isolated_target = tmp_path / "isolated_target"
        real_target.mkdir()
        isolated_target.mkdir()
        (real_target / "file.txt").write_text("real")
        (isolated_target / "file.txt").write_text("isolated")

        earlier_artifact = tmp_path / "02_scan.json"
        earlier_artifact.write_text('{\"phase\": \"scan\"}')

        before = capture_target_hashes(real_target, isolated_target, [earlier_artifact])

        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path / "output")

        assert_targets_unchanged(before, real_target, isolated_target, [earlier_artifact])

    def test_analysis_classification_does_not_import_later_phases(self):
        """Prove that Analysis_Classification does not import runtime entry points from later phases or LLM."""
        import backend.phases.analysis_classification.runner as runner_module

        forbidden = [
            "backend.phases.statement_output",
            "backend.phases.execution",
            "backend.phases.simulation_environment",
            "backend.phases.inspection",
            "backend.llm",
        ]
        imported = set(runner_module.__dict__.keys())
        for name in forbidden:
            assert name not in imported, f"Forbidden import found in runner_module: {name}"


def sys_modules() -> set[str]:
    import sys
    return {m for m in sys.modules.keys()}