"""
Builder for frozen Scan outputs used as Analysis_Classification input.
"""
from typing import Any

from backend.schemas.scan import (
    Scan_Output,
    Scan_File,
    Scan_Surface,
    Scan_Notice,
)


class ScanOutputBuilder:
    """Build a canonical Scan_Output for Analysis_Classification tests."""

    def __init__(self):
        self._data: dict[str, Any] = {
            "phase": "scan",
            "status": "completed",
            "snapshot_fingerprint": "snap-fp-abc123",
            "scan_fingerprint": "scan-fp-def456",
            "target_root": "isolated_target",
            "files": [
                Scan_File(
                    relative_path="isolated_target/src/module.py",
                    file_type="source",
                    language="python",
                    size_bytes=120,
                    sha256="sha256-module-py",
                    category="module",
                ),
                Scan_File(
                    relative_path="isolated_target/tests/test_module.py",
                    file_type="test",
                    language="python",
                    size_bytes=80,
                    sha256="sha256-test-py",
                    category="test",
                ),
                Scan_File(
                    relative_path="isolated_target/pyproject.toml",
                    file_type="config",
                    language="toml",
                    size_bytes=200,
                    sha256="sha256-pyproject",
                    category="config",
                ),
            ],
            "surfaces": [
                Scan_Surface(
                    surface_type="entry_point",
                    identifier="module:main",
                    source_path="isolated_target/src/module.py",
                    evidence="def main",
                ),
            ],
            "notices": [],
            "language_summary": {"python": 2, "toml": 1},
            "surface_summary": {"entry_point": 1},
        }

    def with_phase(self, phase: str) -> "ScanOutputBuilder":
        self._data["phase"] = phase
        return self

    def with_status(self, status: str) -> "ScanOutputBuilder":
        self._data["status"] = status
        return self

    def with_snapshot_fingerprint(self, value: str | None) -> "ScanOutputBuilder":
        self._data["snapshot_fingerprint"] = value
        return self

    def with_scan_fingerprint(self, value: str | None) -> "ScanOutputBuilder":
        self._data["scan_fingerprint"] = value
        return self

    def with_target_root(self, value: str) -> "ScanOutputBuilder":
        self._data["target_root"] = value
        return self

    def _scan_file(self, value: Scan_File | dict[str, Any]) -> Scan_File:
        if isinstance(value, Scan_File):
            return value
        defaults = {
            "file_type": "unknown",
            "language": "unknown",
            "size_bytes": 0,
            "sha256": "",
            "category": "unknown",
        }
        return Scan_File(**{**defaults, **value})

    def _scan_surface(self, value: Scan_Surface | dict[str, Any]) -> Scan_Surface:
        if isinstance(value, Scan_Surface):
            return value
        defaults = {
            "identifier": "",
            "source_path": "",
            "evidence": "",
        }
        return Scan_Surface(**{**defaults, **value})

    def _scan_notice(self, value: Scan_Notice | dict[str, Any]) -> Scan_Notice:
        if isinstance(value, Scan_Notice):
            return value
        defaults = {
            "relative_path": "",
            "reason": "",
        }
        return Scan_Notice(**{**defaults, **value})

    def with_files(self, value: list[Scan_File] | list[dict[str, Any]]) -> "ScanOutputBuilder":
        self._data["files"] = [self._scan_file(f) for f in value]
        # Tests that replace the full file list expect a clean surface list.
        self._data["surfaces"] = []
        return self

    def with_surfaces(self, value: list[Scan_Surface] | list[dict[str, Any]]) -> "ScanOutputBuilder":
        self._data["surfaces"] = [self._scan_surface(s) for s in value]
        return self

    def with_notices(self, value: list[Scan_Notice] | list[dict[str, Any]]) -> "ScanOutputBuilder":
        self._data["notices"] = [self._scan_notice(n) for n in value]
        return self

    def with_language_summary(self, value: dict[str, int]) -> "ScanOutputBuilder":
        self._data["language_summary"] = value
        return self

    def with_surface_summary(self, value: dict[str, int]) -> "ScanOutputBuilder":
        self._data["surface_summary"] = value
        return self

    def build(self) -> Scan_Output:
        return Scan_Output(**self._data)

    def build_dict(self) -> dict[str, Any]:
        return self.build().to_dict()