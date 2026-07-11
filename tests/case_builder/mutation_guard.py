"""
Mutation guard for Inspection tests.

Captures hashes of real target, isolated target, and earlier phase artifacts
before Inspection, then asserts they are unchanged after.
"""
import hashlib
import json
from pathlib import Path
from typing import Any


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_directory(path: Path) -> str:
    """Return a deterministic SHA-256 digest of a directory tree."""
    h = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            relative = file_path.relative_to(path).as_posix()
            h.update(relative.encode("utf-8"))
            h.update(_hash_file(file_path).encode("utf-8"))
    return h.hexdigest()


def capture_target_hashes(
    real_target: Path | None,
    isolated_target: Path | None,
    earlier_artifacts: list[Path] | None = None,
) -> dict[str, Any]:
    """Capture hashes of targets and earlier artifacts."""
    hashes: dict[str, Any] = {}
    if real_target is not None and real_target.exists():
        hashes["real_target"] = _hash_directory(real_target)
    if isolated_target is not None and isolated_target.exists():
        hashes["isolated_target"] = _hash_directory(isolated_target)
    hashes["earlier_artifacts"] = {
        str(p.resolve()): _hash_file(p) for p in (earlier_artifacts or []) if p.exists()
    }
    return hashes


def assert_targets_unchanged(
    before: dict[str, Any],
    real_target: Path | None,
    isolated_target: Path | None,
    earlier_artifacts: list[Path] | None = None,
) -> None:
    """Assert that captured hashes match the current state."""
    after = capture_target_hashes(real_target, isolated_target, earlier_artifacts)
    assert before == after, f"Target or artifact mutation detected:\n{json.dumps({'before': before, 'after': after}, indent=2)}"