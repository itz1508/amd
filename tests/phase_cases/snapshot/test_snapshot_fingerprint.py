"""Test snapshot fingerprint determinism."""
from pathlib import Path
import tempfile

from backend.phases.snapshot.runner import run_snapshot


def test_snapshot_fingerprint_unchanged():
    """Test fingerprint is identical for unchanged content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test target
        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "sample.py").write_text("print('hello')\n", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        # First run
        result1 = run_snapshot(test_target, output_root)
        fingerprint1 = result1.snapshot_fingerprint

        # Second run (unchanged)
        result2 = run_snapshot(test_target, output_root)

        assert result2.snapshot_fingerprint == fingerprint1, "Fingerprints should match for unchanged content"


def test_snapshot_fingerprint_changed():
    """Test fingerprint changes when file content changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test target
        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "sample.py").write_text("print('hello')\n", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        # First run
        result1 = run_snapshot(test_target, output_root)
        fingerprint1 = result1.snapshot_fingerprint

        # Modify file
        (test_target / "sample.py").write_text("print('goodbye')\n", encoding="utf-8")

        # Second run
        result2 = run_snapshot(test_target, output_root)

        assert result2.snapshot_fingerprint != fingerprint1, "Fingerprints should differ after content change"


def test_snapshot_stable_path_ordering():
    """Test files are sorted by relative path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_target = tmpdir / "target"
        test_target.mkdir()
        # Create files in non-alphabetical order
        (test_target / "z_file.txt").write_text("z", encoding="utf-8")
        (test_target / "a_file.txt").write_text("a", encoding="utf-8")
        (test_target / "m_file.txt").write_text("m", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        result = run_snapshot(test_target, output_root)

        # Check ordering
        paths = [f.relative_path for f in result.files]
        assert paths == sorted(paths), "Files should be sorted by relative path"


def test_snapshot_deterministic_json():
    """Test artifact uses stable key ordering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "file.txt").write_text("content", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        result = run_snapshot(test_target, output_root)

        # Check artifact file uses sorted keys
        import json
        artifact_path = output_root / "01_snapshot.json"
        content = artifact_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Parse and re-serialize with sorted keys - should match
        expected = json.dumps(data, sort_keys=True, indent=2)
        assert content == expected, "JSON should use sorted key order"