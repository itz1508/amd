"""Test snapshot with missing target."""
from pathlib import Path
import tempfile

import pytest
from backend.phases.snapshot.runner import run_snapshot


def test_snapshot_missing_target():
    """Test snapshot handles missing target path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_root = tmpdir / "output"
        output_root.mkdir()

        # Run snapshot with non-existent target
        with pytest.raises(ValueError, match="does not exist"):
            run_snapshot(tmpdir / "nonexistent", output_root)


def test_snapshot_target_is_file():
    """Test snapshot handles target that is a file, not directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create a file as target
        test_file = tmpdir / "test.txt"
        test_file.write_text("test content")

        output_root = tmpdir / "output"
        output_root.mkdir()

        # Run snapshot with file as target
        with pytest.raises(ValueError, match="not a directory"):
            run_snapshot(test_file, output_root)