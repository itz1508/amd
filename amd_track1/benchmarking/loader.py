"""Benchmarking manifest and fixture loader.

Loads suite manifests from ``amd_track1/benchmarking/suites`` and case
fixtures from ``amd_track1/benchmarking/fixtures``. Provides deterministic
ordering and basic validation so the runner can trust the inputs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Fixture, SuiteManifest


_BENCHMARKING_DIR = Path(__file__).resolve().parent
_SUITES_DIR = _BENCHMARKING_DIR / "suites"
_FIXTURES_DIR = _BENCHMARKING_DIR / "fixtures"


def _manifest_path(suite_id: str) -> Path:
    return _SUITES_DIR / f"{suite_id}.json"


def _fixture_path(suite_id: str) -> Path:
    return _FIXTURES_DIR / f"{suite_id}.jsonl"


def list_suite_ids() -> List[str]:
    """Return all suite IDs discovered from the suites directory."""
    return sorted(p.stem for p in _SUITES_DIR.glob("*.json") if p.is_file())


def load_suite(suite_id: str) -> SuiteManifest:
    """Load and return a suite manifest by ID.

    Raises ``FileNotFoundError`` or ``ValueError`` if the manifest cannot be
    loaded or parsed.
    """
    path = _manifest_path(suite_id)
    if not path.exists():
        raise FileNotFoundError(f"suite manifest not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid suite manifest JSON: {exc}") from exc
    return SuiteManifest.from_dict(payload)


def load_fixtures(suite_id: str) -> List[Fixture]:
    """Load fixtures for a suite from its JSONL file.

    Returns fixtures in deterministic file order.
    """
    manifest_path = _manifest_path(suite_id)
    candidates = [_fixture_path(suite_id)]
    if manifest_path.exists():
        try:
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            fixture_path = manifest_payload.get("fixture_path")
            if fixture_path:
                resolved = _BENCHMARKING_DIR / fixture_path
                candidates.append(resolved)
        except (json.JSONDecodeError, OSError):
            pass

    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return []
    text = path.read_text(encoding="utf-8")
    fixtures: List[Fixture] = []
    decoder = json.JSONDecoder()
    idx = 0
    length = len(text)
    while idx < length:
        char = text[idx]
        if char in "\r\n\t ":
            idx += 1
            continue
        try:
            payload, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        fixtures.append(Fixture.from_dict(payload))
        idx = end
    return fixtures


def load_suite_with_fixtures(suite_id: str) -> Tuple[SuiteManifest, List[Fixture]]:
    """Convenience loader returning both manifest and fixtures."""
    manifest = load_suite(suite_id)
    fixtures = load_fixtures(suite_id)
    return manifest, fixtures


def validate_suite(suite_id: str) -> List[str]:
    """Lightweight validation of a suite manifest and its fixtures.

    Returns a list of human-readable issues. An empty list means the suite
    appears valid.
    """
    issues: List[str] = []
    try:
        manifest = load_suite(suite_id)
    except (FileNotFoundError, ValueError) as exc:
        return [str(exc)]

    if manifest.suite_id != suite_id:
        issues.append(f"suite_id mismatch in manifest: {manifest.suite_id}")
    if not manifest.fixture_path:
        issues.append("fixture_path is required")
    if not manifest.capability_ids:
        issues.append("capability_ids is required")
    if manifest.repetitions < 1:
        issues.append("repetitions must be >= 1")
    if manifest.warmup_runs < 0:
        issues.append("warmup_runs must be >= 0")
    if manifest.timeout_ms <= 0:
        issues.append("timeout_ms must be > 0")

    fixtures = load_fixtures(suite_id)
    if not fixtures:
        issues.append("fixture file is empty or missing")
    else:
        for fixture in fixtures:
            if fixture.suite_id != suite_id:
                issues.append(f"fixture suite_id mismatch: {fixture.suite_id}")
            if not fixture.fixture_id:
                issues.append("fixture_id is required")
            if not fixture.prompt:
                issues.append("prompt is required")

    return issues