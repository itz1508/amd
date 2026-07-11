"""Test snapshot output boundary enforcement."""
from pathlib import Path
import tempfile

import pytest
from backend.phases.snapshot.runner import run_snapshot
from backend.paths import OutputBoundaryError


def test_snapshot_output_equals_target():
    """Test snapshot rejects output_root equal to target_root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test target
        test_target = tmpdir / "target"
        test_target.mkdir()

        # Run snapshot with output equals target
        with pytest.raises(OutputBoundaryError, match="cannot equal"):
            run_snapshot(test_target, test_target)


def test_snapshot_output_inside_target():
    """Test snapshot rejects output_root inside target_root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test target
        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "file.txt").write_text("content", encoding="utf-8")

        # Create output inside target
        output_root = test_target / "output"

        # Run snapshot with output inside target
        with pytest.raises(OutputBoundaryError, match="cannot be inside"):
            run_snapshot(test_target, output_root)