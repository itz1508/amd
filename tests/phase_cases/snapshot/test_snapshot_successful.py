"""Test successful snapshot capture."""
from pathlib import Path
import tempfile

from backend.phases.snapshot.runner import run_snapshot


def test_snapshot_successful_capture():
    """Test snapshot captures files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test target
        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "file1.txt").write_text("content1", encoding="utf-8")
        (test_target / "file2.py").write_text("print('hello')", encoding="utf-8")

        # Create output directory separate from target
        output_root = tmpdir / "output"
        output_root.mkdir()

        # Run snapshot
        result = run_snapshot(test_target, output_root)

        assert result.status in ("completed", "completed_with_notices")

        # Verify artifact exists
        artifact_path = output_root / "01_snapshot.json"
        assert artifact_path.exists(), "01_snapshot.json not found"

        # Verify files captured
        assert len(result.files) == 2
        relative_paths = [f.relative_path for f in result.files]
        assert "file1.txt" in relative_paths
        assert "file2.py" in relative_paths

        # Verify fingerprint
        assert result.snapshot_fingerprint
        assert len(result.snapshot_fingerprint) == 64  # SHA-256 hex length