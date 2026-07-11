"""
Scan runner - main entry point.
"""
import hashlib
import json
import sys
from pathlib import Path
from backend.schemas.snapshot import Snapshot_Output, SnapshotFile, SnapshotNotice
from backend.schemas.scan import Scan_Output, Scan_File, Scan_Surface, Scan_Notice
from backend.paths import resolve_output_root, OutputBoundaryError
from backend.artifact_store.writer import write_json_artifact, ArtifactWriteError


# Language extensions mapping
LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".pyx": "cython",
    ".pyi": "python",
    ".toml": "toml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".cfg": "ini",
    ".ini": "ini",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".sh": "shell",
    ".ps1": "powershell",
    "": "unknown",
}

# File type classification by path patterns
SOURCE_PATTERNS = ["src/", "backend/", "library/", "lib/"]
TEST_PATTERNS = ["tests/", "test_", "/test_", "_test.", ".test."]
CONFIG_PATTERNS = ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", ".gitignore", "README", "LICENSE", "*.json", "*.toml", "*.yaml", "*.yml", "*.ini", "*.cfg"]
BUILD_PATTERNS = ["build/", "dist/", "*.egg-info/", ".pytest_cache/", ".mypy_cache/", "__pycache__/", "*.pyc"]


def classify_file_type(relative_path: str) -> str:
    """Classify file type based on path patterns."""
    path_lower = relative_path.lower()
    
    # Check build artifacts
    for pattern in BUILD_PATTERNS:
        if pattern.endswith("/"):
            if pattern[:-1] in path_lower or path_lower.startswith(pattern):
                return "build"
        elif pattern.startswith("*."):
            if path_lower.endswith(pattern[1:]):
                return "build"
        else:
            if path_lower == pattern.lower() or pattern in path_lower:
                return "build"
    
    # Check source
    for pattern in SOURCE_PATTERNS:
        if path_lower.startswith(pattern.lower()):
            return "source"
    
    # Check test
    for pattern in TEST_PATTERNS:
        if pattern.startswith("/"):
            if pattern[1:] in path_lower:
                return "test"
        elif pattern.endswith("."):
            if path_lower.endswith(pattern):
                return "test"
        else:
            if path_lower.startswith(pattern.lower()):
                return "test"
    
    # Check config
    for pattern in CONFIG_PATTERNS:
        if pattern.startswith("*."):
            if path_lower.endswith(pattern[1:]):
                return "config"
        else:
            if path_lower == pattern.lower():
                return "config"
    
    return "other"


def detect_language(relative_path: str) -> str | None:
    """Detect language from file extension."""
    ext = Path(relative_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext, None)


def classify_category(relative_path: str, file_type: str) -> str:
    """Classify file category."""
    path_lower = relative_path.lower()
    
    if file_type == "source":
        if "__init__.py" in path_lower:
            return "package"
        elif path_lower.endswith(".py"):
            return "module"
        return "source"
    elif file_type == "test":
        return "test"
    elif file_type == "config":
        return "config"
    elif file_type == "build":
        return "build"
    elif path_lower.endswith(".md"):
        return "documentation"
    
    return "other"


def identify_surfaces(relative_path: str, content: str | None = None) -> list[Scan_Surface]:
    """Identify repository surfaces from file path and content.
    
    Ensures every surface source_path corresponds to a captured Scan_File.
    """
    surfaces: list[Scan_Surface] = []
    path_lower = relative_path.lower()
    
    # Check for main entry points
    if "__main__.py" in path_lower:
        surfaces.append(Scan_Surface(
            surface_type="entry_point",
            identifier="__main__",
            source_path=relative_path,
            evidence="Python package main entry"
        ))
    
    # Check for CLI entry points
    if "cli.py" in path_lower or "_cli." in path_lower:
        surfaces.append(Scan_Surface(
            surface_type="entry_point",
            identifier="cli",
            source_path=relative_path,
            evidence="CLI entry point detected"
        ))
    
    # Check for setup files
    if "pyproject.toml" in path_lower:
        surfaces.append(Scan_Surface(
            surface_type="build_config",
            identifier="pyproject.toml",
            source_path=relative_path,
            evidence="Build configuration"
        ))
    
    if "setup.py" in path_lower:
        surfaces.append(Scan_Surface(
            surface_type="build_config",
            identifier="setup.py",
            source_path=relative_path,
            evidence="Legacy build script"
        ))
    
    return surfaces


def load_snapshot(snapshot_input: Snapshot_Output | str | Path) -> Snapshot_Output:
    """Load snapshot from file path or return if already loaded."""
    if isinstance(snapshot_input, Snapshot_Output):
        return snapshot_input
    
    snapshot_path = Path(snapshot_input)
    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Convert from dict to Snapshot_Output
    return Snapshot_Output(
        phase=data["phase"],
        target_root=data["target_root"],
        status=data["status"],
        files=[SnapshotFile(
            relative_path=sf["relative_path"],
            extension=sf["extension"],
            size_bytes=sf["size_bytes"],
            sha256=sf["sha256"],
            read_status=sf["read_status"]
        ) for sf in data["files"]],
        notices=[SnapshotNotice(
            notice_code=n["notice_code"],
            relative_path=n["relative_path"],
            reason=n["reason"],
            evidence=n.get("evidence")
        ) for n in data["notices"]],
        snapshot_fingerprint=data["snapshot_fingerprint"]
    )


def compute_scan_fingerprint(
    files: list[Scan_File],
    surfaces: list[Scan_Surface],
    notices: list[Scan_Notice],
) -> str:
    """Compute deterministic fingerprint from stable Scan content."""
    payload = {
        "files": sorted([
            {
                "relative_path": f.relative_path,
                "file_type": f.file_type,
                "language": f.language,
                "category": f.category,
            }
            for f in files
        ], key=lambda x: x["relative_path"]),
        "surfaces": sorted([
            {
                "surface_type": s.surface_type,
                "identifier": s.identifier,
                "source_path": s.source_path,
            }
            for s in surfaces
        ], key=lambda x: (x["surface_type"], x["identifier"])),
        "notices": sorted([
            {
                "notice_code": n.notice_code,
                "relative_path": n.relative_path,
                "reason": n.reason,
            }
            for n in notices
        ], key=lambda x: (x["notice_code"], x["relative_path"])),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_snapshot(snapshot: Snapshot_Output) -> None:
    """Validate snapshot artifact for Scan consumption."""
    if snapshot.phase != "snapshot":
        raise ValueError(f"Expected phase 'snapshot', got '{snapshot.phase}'")
    
    if not snapshot.snapshot_fingerprint:
        raise ValueError("Snapshot fingerprint is missing")
    
    if snapshot.status not in ("completed", "completed_with_notices"):
        raise ValueError(f"Unacceptable snapshot status: {snapshot.status}")


def run_scan(
    snapshot: Snapshot_Output | str | Path,
    output_root: str | Path,
) -> Scan_Output:
    """Run scan phase on snapshot output.
    
    Args:
        snapshot: Snapshot_Output object or path to 01_snapshot.json.
        output_root: Output directory path (must be outside target).
        
    Returns:
        Scan_Output with discovered repository surfaces.
        
    Raises:
        ValueError: If snapshot is invalid or wrong phase.
        OutputBoundaryError: If output_root is inside target.
        ArtifactWriteError: If artifact write fails.
    """
    # Load snapshot if it's a path
    snapshot_obj = load_snapshot(snapshot)
    
    # Validate snapshot
    validate_snapshot(snapshot_obj)
    
    # Resolve output root relative to target
    target_root = Path(snapshot_obj.target_root)
    output_path = resolve_output_root(output_root, target_root)
    
    # Process each file from snapshot
    scan_files: list[Scan_File] = []
    scan_surfaces: list[Scan_Surface] = []
    scan_notices: list[Scan_Notice] = []
    language_summary: dict[str, int] = {}
    surface_summary: dict[str, int] = {}
    
    # Propagate snapshot notices as scan notices
    for notice in snapshot_obj.notices:
        scan_notices.append(Scan_Notice(
            notice_code=notice.notice_code,
            relative_path=notice.relative_path,
            reason=notice.reason,
            evidence=notice.evidence
        ))
    
    # Process files
    for snap_file in snapshot_obj.files:
        if snap_file.read_status != "readable":
            scan_notices.append(Scan_Notice(
                notice_code="unreadable",
                relative_path=snap_file.relative_path,
                reason=f"File not readable: {snap_file.read_status}",
                evidence=snap_file.relative_path
            ))
            continue
        
        # Classify file
        file_type = classify_file_type(snap_file.relative_path)
        language = detect_language(snap_file.relative_path)
        category = classify_category(snap_file.relative_path, file_type)
        
        scan_file = Scan_File(
            relative_path=snap_file.relative_path,
            file_type=file_type,
            language=language,
            size_bytes=snap_file.size_bytes,
            sha256=snap_file.sha256,
            category=category
        )
        scan_files.append(scan_file)
        
        # Update language summary
        lang_key = language or "unknown"
        language_summary[lang_key] = language_summary.get(lang_key, 0) + 1
        
        # Identify surfaces - every surface source_path corresponds to a captured Scan_File
        surfaces = identify_surfaces(snap_file.relative_path)
        scan_surfaces.extend(surfaces)
        for surface in surfaces:
            surface_summary[surface.surface_type] = surface_summary.get(surface.surface_type, 0) + 1
    
    # Sort for deterministic output
    scan_files.sort(key=lambda f: f.relative_path)
    scan_surfaces.sort(key=lambda s: (s.surface_type, s.identifier, s.source_path))
    scan_notices.sort(key=lambda n: (n.notice_code, n.relative_path))
    
    # Compute fingerprint
    scan_fingerprint = compute_scan_fingerprint(scan_files, scan_surfaces, scan_notices)
    
    # Determine status
    status = "completed" if not scan_notices else "completed_with_notices"
    
    # Write artifact
    artifact_path = output_path / "02_scan.json"
    scan_output = Scan_Output(
        phase="scan",
        snapshot_fingerprint=snapshot_obj.snapshot_fingerprint,
        target_root=snapshot_obj.target_root,
        status=status,
        files=scan_files,
        surfaces=scan_surfaces,
        notices=scan_notices,
        scan_fingerprint=scan_fingerprint,
        language_summary=language_summary,
        surface_summary=surface_summary,
    )
    
    try:
        write_json_artifact(artifact_path, scan_output.to_dict())
    except ArtifactWriteError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    
    return scan_output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for scan phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="scan",
        description="Scan phase - discover repository surfaces"
    )
    parser.add_argument(
        "snapshot",
        help="Path to 01_snapshot.json artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts (required, must be outside target)"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        result = run_scan(parsed.snapshot, parsed.output_root)
        print(f"Scan completed: {parsed.snapshot}")
        print(f"  Files scanned: {len(result.files)}")
        print(f"  Surfaces found: {len(result.surfaces)}")
        print(f"  Notices: {len(result.notices)}")
        print(f"  Languages: {result.language_summary}")
        print(f"  Surfaces: {result.surface_summary}")
        print(f"  Output: {Path(parsed.output_root) / '02_scan.json'}")
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except OutputBoundaryError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ArtifactWriteError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
