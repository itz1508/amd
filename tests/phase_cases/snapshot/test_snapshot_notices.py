"""Test snapshot exclusion and unreadable handling."""
from pathlib import Path
import tempfile

from backend.phases.snapshot.runner import run_snapshot


def test_snapshot_exclusion_notice():
    """Test snapshot emits notice for excluded directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "file.txt").write_text("content", encoding="utf-8")

        # Create excluded directory
        (test_target / ".venv").mkdir()
        (test_target / ".venv" / "some_package").mkdir()
        (test_target / ".venv" / "some_package" / "script.py").write_text("print('pkg')", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        result = run_snapshot(test_target, output_root)

        # Should have exclusion notices
        excluded_notices = [n for n in result.notices if n.notice_code == "excluded"]
        assert len(excluded_notices) >= 1, "Expected at least one exclusion notice"

        # Should not have traversed inside .venv
        venv_files = [f for f in result.files if f.relative_path.startswith(".venv/")]
        assert len(venv_files) == 0, "Files inside .venv should not be captured"


def test_snapshot_excludes_tooling_artifacts_and_secret_files():
    """Snapshot should skip local tooling, generated artifacts, and secret files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_target = tmpdir / "target"
        test_target.mkdir()
        (test_target / "src").mkdir()
        (test_target / "src" / "app.py").write_text("print('ok')", encoding="utf-8")
        (test_target / ".env").write_text("SECRET=value", encoding="utf-8")

        for folder_name in [".workbench-venv", ".codex", ".kiro", ".agents", "input", "output", "runs"]:
            folder = test_target / folder_name
            folder.mkdir()
            (folder / "noise.py").write_text("print('noise')", encoding="utf-8")

        output_root = tmpdir / "output_root"
        output_root.mkdir()

        result = run_snapshot(test_target, output_root)
        captured = {f.relative_path for f in result.files}
        notices = {n.relative_path for n in result.notices if n.notice_code == "excluded"}

        assert "src\\app.py" in captured or "src/app.py" in captured
        assert ".env" not in captured
        for folder_name in [".workbench-venv", ".codex", ".kiro", ".agents", "input", "output", "runs"]:
            assert not any(path.startswith(folder_name) for path in captured)
            assert folder_name in notices


def test_snapshot_no_target_mutation():
    """Test snapshot does not modify target files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        test_target = tmpdir / "target"
        test_target.mkdir()
        test_file = test_target / "file.txt"
        test_file.write_text("original content", encoding="utf-8")

        output_root = tmpdir / "output"
        output_root.mkdir()

        result = run_snapshot(test_target, output_root)

        # Check no files created inside target
        target_files = [f.name for f in test_target.iterdir()]
        assert "file.txt" in target_files
        assert len(target_files) == 1, "No extra files should be created in target"

        # Check no hidden files created
        hidden_in_target = [f for f in test_target.iterdir() if f.name.startswith(".")]
        assert len(hidden_in_target) == 0, "No hidden files should be created in target"
