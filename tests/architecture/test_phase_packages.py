"""Test that all nine canonical phase packages exist and are importable."""
import pytest
import sys
from pathlib import Path


# Nine canonical phases
CANONICAL_PHASES = [
    "snapshot",
    "scan", 
    "analysis_classification",
    "statement_output",
    "gap_evaluation",
    "simulation_environment",
    "inspection",
    "final_result",
    "cleanup",
]


class TestCanonicalPhasePackages:
    """Test that all canonical phase packages exist."""

    def test_snapshot_package_exists(self):
        """Snapshot phase package can be imported."""
        import backend.phases.snapshot
        assert backend.phases.snapshot is not None

    def test_scan_package_exists(self):
        """Scan phase package can be imported."""
        import backend.phases.scan
        assert backend.phases.scan is not None

    def test_analysis_classification_package_exists(self):
        """Analysis_Classification phase package can be imported."""
        import backend.phases.analysis_classification
        assert backend.phases.analysis_classification is not None

    def test_statement_output_package_exists(self):
        """Statement_Output phase package can be imported."""
        import backend.phases.statement_output
        assert backend.phases.statement_output is not None

    def test_gap_evaluation_package_exists(self):
        """Gap_Evaluation phase package can be imported."""
        import backend.phases.gap_evaluation
        assert backend.phases.gap_evaluation is not None

    def test_simulation_environment_package_exists(self):
        """Simulation_Environment phase package can be imported."""
        import backend.phases.simulation_environment
        assert backend.phases.simulation_environment is not None

    def test_inspection_package_exists(self):
        """Inspection phase package can be imported."""
        import backend.phases.inspection
        assert backend.phases.inspection is not None

    def test_final_result_package_exists(self):
        """Final_Result phase package can be imported."""
        import backend.phases.final_result
        assert backend.phases.final_result is not None

    def test_cleanup_package_exists(self):
        """Cleanup phase package can be imported."""
        import backend.phases.cleanup
        assert backend.phases.cleanup is not None


class TestCanonicalRunnersImport:
    """Test that all canonical runners can be imported."""

    def test_snapshot_runner_imports(self):
        """Snapshot runner can be imported."""
        from backend.phases.snapshot.runner import run_snapshot
        assert run_snapshot is not None

    def test_scan_runner_imports(self):
        """Scan runner can be imported."""
        from backend.phases.scan.runner import run_scan
        assert run_scan is not None

    def test_analysis_classification_runner_imports(self):
        """Analysis_Classification runner can be imported."""
        from backend.phases.analysis_classification.runner import run_analysis_classification
        assert run_analysis_classification is not None

    def test_statement_output_runner_imports(self):
        """Statement_Output runner can be imported."""
        from backend.phases.statement_output.runner import run_statement_output
        assert run_statement_output is not None

    def test_gap_evaluation_runner_imports(self):
        """Gap_Evaluation runner can be imported."""
        from backend.phases.gap_evaluation.runner import run_gap_evaluation
        assert run_gap_evaluation is not None

    def test_simulation_environment_runner_imports(self):
        """Simulation_Environment runner can be imported."""
        from backend.phases.simulation_environment.runner import run_simulation_environment
        assert run_simulation_environment is not None

    def test_inspection_runner_imports(self):
        """Inspection runner can be imported."""
        from backend.phases.inspection.runner import run_inspection
        assert run_inspection is not None

    def test_final_result_runner_imports(self):
        """Final_Result runner can be imported."""
        from backend.phases.final_result.runner import run_final_result
        assert run_final_result is not None

    def test_cleanup_runner_imports(self):
        """Cleanup runner can be imported."""
        from backend.phases.cleanup.runner import run_cleanup_retention
        assert run_cleanup_retention is not None


class TestPyprojectPackaging:
    """Test that only src/backend is packaged by pyproject.toml."""

    def test_pyproject_packages_only_backend(self):
        """pyproject.toml packages only src/backend."""
        import tomllib
        import os
        pyproject_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml"))
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        
        # Check hatch build targets
        wheel_packages = config.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {}).get("packages", [])
        
        assert wheel_packages == ["src/backend"], f"Expected only ['src/backend'], got {wheel_packages}"


class TestRuntimePackageResolution:
    """Test that tests and runtime resolve the same backend package."""

    def test_backend_package_resolution(self):
        """Tests and runtime resolve the same backend package."""
        import backend
        
        # Get the backend module path
        backend_path = backend.__file__
        
        # Verify it's in the expected location
        expected_path = "D:\\Dev\\amd\\src\\backend\\__init__.py"
        assert backend_path == expected_path, \
            f"backend resolved from {backend_path}, expected {expected_path}"


class TestPhaseTestDirectories:
    """Test that every phase test directory is collected by complete-suite command."""

    def test_snapshot_test_directory_exists(self):
        """Snapshot phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\snapshot")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_scan_test_directory_exists(self):
        """Scan phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\scan")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_analysis_classification_test_directory_exists(self):
        """Analysis_Classification phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\analysis_classification")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_statement_output_test_directory_exists(self):
        """Statement_Output phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\statement_output")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_gap_evaluation_test_directory_exists(self):
        """Gap_Evaluation phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\gap_evaluation")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_simulation_environment_test_directory_exists(self):
        """Simulation_Environment phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\simulation_environment")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_inspection_test_directory_exists(self):
        """Inspection phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\inspection")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"

    def test_final_result_test_file_exists(self):
        """Final_Result phase test file exists."""
        test_file = Path(r"D:\Dev\amd\tests\phase_cases\test_final_result.py")
        assert test_file.exists(), f"Final result test file not found: {test_file}"

    def test_cleanup_test_directory_exists(self):
        """Cleanup phase test directory exists."""
        test_dir = Path(r"D:\Dev\amd\tests\phase_cases\cleanup")
        assert test_dir.exists(), f"Test directory not found: {test_dir}"
        assert test_dir.is_dir(), f"Test path is not a directory: {test_dir}"