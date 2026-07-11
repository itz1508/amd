"""Test backend.phases.scan functionality."""
import json
import tempfile
from pathlib import Path
import pytest

from backend.schemas.snapshot import Snapshot_Output, SnapshotFile, SnapshotNotice
from backend.schemas.scan import Scan_Output, Scan_File, Scan_Surface, Scan_Notice
from backend.phases.scan import run_scan, validate_snapshot, load_snapshot


@pytest.fixture
def valid_snapshot_dict():
    """Create a valid snapshot dictionary."""
    return {
        "phase": "snapshot",
        "target_root": "/tmp/target",
        "status": "completed",
        "files": [
            {
                "relative_path": "src/module.py",
                "extension": ".py",
                "size_bytes": 100,
                "sha256": "abc123",
                "read_status": "readable"
            },
            {
                "relative_path": "tests/test_module.py",
                "extension": ".py",
                "size_bytes": 200,
                "sha256": "def456",
                "read_status": "readable"
            },
            {
                "relative_path": "README.md",
                "extension": ".md",
                "size_bytes": 50,
                "sha256": "ghi789",
                "read_status": "readable"
            }
        ],
        "notices": [],
        "snapshot_fingerprint": "fingerprint123"
    }


@pytest.fixture
def valid_snapshot_obj(valid_snapshot_dict):
    """Create a Snapshot_Output object."""
    return Snapshot_Output(
        phase=valid_snapshot_dict["phase"],
        target_root=valid_snapshot_dict["target_root"],
        status=valid_snapshot_dict["status"],
        files=[
            SnapshotFile(
                relative_path=f["relative_path"],
                extension=f["extension"],
                size_bytes=f["size_bytes"],
                sha256=f["sha256"],
                read_status=f["read_status"]
            )
            for f in valid_snapshot_dict["files"]
        ],
        notices=[
            SnapshotNotice(
                notice_code=n["notice_code"],
                relative_path=n["relative_path"],
                reason=n["reason"],
                evidence=n.get("evidence")
            )
            for n in valid_snapshot_dict["notices"]
        ],
        snapshot_fingerprint=valid_snapshot_dict["snapshot_fingerprint"]
    )


class TestBackendScanImports:
    """Test that backend.phases.scan imports work."""
    
    def test_scan_output_import(self):
        """Scan_Output can be imported from backend.schemas.scan."""
        assert Scan_Output is not None
    
    def test_scan_file_import(self):
        """Scan_File can be imported from backend.schemas.scan."""
        assert Scan_File is not None
    
    def test_scan_surface_import(self):
        """Scan_Surface can be imported from backend.schemas.scan."""
        assert Scan_Surface is not None
    
    def test_scan_notice_import(self):
        """Scan_Notice can be imported from backend.schemas.scan."""
        assert Scan_Notice is not None
    
    def test_run_scan_import(self):
        """run_scan can be imported from backend.phases.scan."""
        assert run_scan is not None


class TestBackendScanValidation:
    """Test snapshot validation for backend scan."""
    
    def test_valid_snapshot_obj(self, valid_snapshot_obj):
        """Valid Snapshot_Output object passes validation."""
        validate_snapshot(valid_snapshot_obj)
    
    def test_wrong_phase_rejected(self, valid_snapshot_dict):
        """Snapshot with wrong phase is rejected."""
        snapshot = Snapshot_Output(
            phase="wrong",
            target_root=valid_snapshot_dict["target_root"],
            status=valid_snapshot_dict["status"],
            files=[],
            notices=[],
            snapshot_fingerprint=valid_snapshot_dict["snapshot_fingerprint"]
        )
        with pytest.raises(ValueError, match="Expected phase 'snapshot'"):
            validate_snapshot(snapshot)


class TestBackendScanExecution:
    """Test run_scan execution."""
    
    def test_run_scan_produces_scan_output(self, valid_snapshot_obj, tmp_path):
        """run_scan produces Scan_Output."""
        result = run_scan(valid_snapshot_obj, tmp_path)
        assert isinstance(result, Scan_Output)
        assert result.phase == "scan"
    
    def test_run_scan_writes_artifact(self, valid_snapshot_obj, tmp_path):
        """run_scan writes 02_scan.json."""
        run_scan(valid_snapshot_obj, tmp_path)
        artifact_path = tmp_path / "02_scan.json"
        assert artifact_path.exists()
    
    def test_artifact_is_valid_json(self, valid_snapshot_obj, tmp_path):
        """02_scan.json is valid JSON."""
        run_scan(valid_snapshot_obj, tmp_path)
        with open(tmp_path / "02_scan.json", 'r') as f:
            data = json.load(f)
        assert isinstance(data, dict)
    
    def test_artifact_has_all_fields(self, valid_snapshot_obj, tmp_path):
        """02_scan.json has all required fields."""
        run_scan(valid_snapshot_obj, tmp_path)
        with open(tmp_path / "02_scan.json", 'r') as f:
            data = json.load(f)
        
        required_fields = ["phase", "snapshot_fingerprint", "target_root", "status", 
                         "files", "surfaces", "notices", "scan_fingerprint",
                         "language_summary", "surface_summary"]
        for field in required_fields:
            assert field in data
    
    def test_files_classified(self, valid_snapshot_obj, tmp_path):
        """Files are classified with type, language, category."""
        result = run_scan(valid_snapshot_obj, tmp_path)
        assert len(result.files) == len(valid_snapshot_obj.files)
        for f in result.files:
            assert f.relative_path
            assert f.file_type
            assert f.category
    
    def test_language_summary_populated(self, valid_snapshot_obj, tmp_path):
        """Language summary is populated."""
        result = run_scan(valid_snapshot_obj, tmp_path)
        assert result.language_summary
        assert "python" in result.language_summary
        assert "markdown" in result.language_summary
    
    def test_scan_fingerprint_present(self, valid_snapshot_obj, tmp_path):
        """scan_fingerprint is present and non-empty."""
        result = run_scan(valid_snapshot_obj, tmp_path)
        assert result.scan_fingerprint
        assert len(result.scan_fingerprint) == 64  # SHA-256 hex
    
    def test_surface_source_path_in_files(self, tmp_path):
        """Every surface source_path corresponds to a captured Scan_File."""
        # Create snapshot with surface files
        snapshot = Snapshot_Output(
            phase="snapshot",
            target_root="/tmp/target",
            status="completed",
            files=[
                SnapshotFile("src/__main__.py", ".py", 100, "abc", "readable"),
                SnapshotFile("pyproject.toml", ".toml", 50, "def", "readable"),
                SnapshotFile("src/module.py", ".py", 100, "ghi", "readable"),
            ],
            notices=[],
            snapshot_fingerprint="fp123"
        )
        
        result = run_scan(snapshot, tmp_path)
        
        # Check all surface source_paths are in file relative_paths
        surface_paths = {s.source_path for s in result.surfaces}
        file_paths = {f.relative_path for f in result.files}
        
        # Every surface path should have a corresponding file
        for surface_path in surface_paths:
            assert surface_path in file_paths, f"Surface path {surface_path} not found in files"
