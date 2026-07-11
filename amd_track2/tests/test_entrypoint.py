"""Tests for entrypoint orchestrator."""

import json
import os
import tempfile

from amd_track2.entrypoint import Track2Orchestrator


def test_fallback_result():
    """Should generate fallback result with all styles."""
    orch = Track2Orchestrator()
    result = orch._fallback_result("task1", ["formal", "sarcastic"])
    assert result["task_id"] == "task1"
    assert "captions" in result
    assert "formal" in result["captions"]
    assert "sarcastic" in result["captions"]
    assert result["captions"]["formal"] != ""


def test_read_input_list_format():
    """Should read list-formatted input."""
    orch = Track2Orchestrator()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump([{"task_id": "t1", "video_url": "http://example.com/v.mp4", "styles": ["formal"]}], f)
        path = f.name

    try:
        orch.input_path = path
        tasks = orch._read_input()
        assert tasks is not None
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "t1"
    finally:
        os.unlink(path)


def test_read_input_dict_format():
    """Should read dict-formatted input with tasks key."""
    orch = Track2Orchestrator()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(
            {
                "tasks": [
                    {
                        "task_id": "t1",
                        "video_url": "http://example.com/v.mp4",
                        "styles": ["formal"],
                    }
                ]
            },
            f,
        )
        path = f.name

    try:
        orch.input_path = path
        tasks = orch._read_input()
        assert tasks is not None
        assert len(tasks) == 1
    finally:
        os.unlink(path)


def test_read_input_missing_file():
    """Should return None for missing file."""
    orch = Track2Orchestrator()
    orch.input_path = "/nonexistent/tasks.json"
    tasks = orch._read_input()
    assert tasks is None


def test_read_input_invalid_json():
    """Should return None for invalid JSON."""
    orch = Track2Orchestrator()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        f.write("not json")
        path = f.name

    try:
        orch.input_path = path
        tasks = orch._read_input()
        assert tasks is None
    finally:
        os.unlink(path)


def test_safe_unlink():
    """Should safely unlink files."""
    orch = Track2Orchestrator()
    # Should not raise on None
    orch._safe_unlink(None)
    # Should not raise on missing file
    orch._safe_unlink("/nonexistent/file.txt")


def test_emergency_write():
    """Should write results as last resort."""
    orch = Track2Orchestrator()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "results.json")
        orch.output_path = path
        orch._emergency_write([{"task_id": "t1", "captions": {"formal": "test"}}])
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1


def test_orchestrator_init():
    """Should initialize all components."""
    orch = Track2Orchestrator()
    assert orch.fetcher is not None
    assert orch.prober is not None
    assert orch.extractor is not None
    assert orch.vision is not None
    assert orch.context_extractor is not None
    assert orch.caption_writer is not None
    assert orch.gap_checker is not None
    assert orch.output_validator is not None