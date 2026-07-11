"""Tests for output_validator module."""

import json
import os
import tempfile

from amd_track2.output_validator import OutputValidator


def test_validate_empty_list():
    """Should validate empty list against empty input."""
    validator = OutputValidator()
    errors = validator._validate([], [])
    assert len(errors) == 0


def test_validate_missing_task_id():
    """Should detect missing task_id."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = [{"captions": {"formal": "test"}}]
    errors = validator._validate(results, input_tasks)
    assert any("missing task_id" in e for e in errors)


def test_validate_duplicate_task_id():
    """Should detect duplicate task_ids."""
    validator = OutputValidator()
    input_tasks = [
        {"task_id": "t1", "styles": ["formal"]},
        {"task_id": "t2", "styles": ["formal"]},
    ]
    results = [
        {"task_id": "t1", "captions": {"formal": "a"}},
        {"task_id": "t1", "captions": {"formal": "b"}},
    ]
    errors = validator._validate(results, input_tasks)
    assert any("Duplicate task_id" in e for e in errors)


def test_validate_unknown_task_id():
    """Should detect unknown task_id."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = [{"task_id": "t99", "captions": {"formal": "test"}}]
    errors = validator._validate(results, input_tasks)
    assert any("Unknown task_id" in e for e in errors)


def test_validate_missing_style():
    """Should detect missing required style."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal", "sarcastic"]}]
    results = [{"task_id": "t1", "captions": {"formal": "test"}}]
    errors = validator._validate(results, input_tasks)
    assert any("missing required style 'sarcastic'" in e for e in errors)


def test_validate_empty_caption():
    """Should detect empty caption string."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = [{"task_id": "t1", "captions": {"formal": "   "}}]
    errors = validator._validate(results, input_tasks)
    assert any("empty" in e for e in errors)


def test_validate_non_string_caption():
    """Should detect non-string caption value."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = [{"task_id": "t1", "captions": {"formal": 123}}]
    errors = validator._validate(results, input_tasks)
    assert any("not a string" in e for e in errors)


def test_validate_count_mismatch():
    """Should detect result count mismatch."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = []
    errors = validator._validate(results, input_tasks)
    assert any("count" in e for e in errors)


def test_repair_fills_missing():
    """Should fill missing results with fallbacks."""
    validator = OutputValidator()
    input_tasks = [
        {"task_id": "t1", "styles": ["formal", "sarcastic"]},
        {"task_id": "t2", "styles": ["formal"]},
    ]
    results = [{"task_id": "t1", "captions": {"formal": "ok"}}]
    repaired = validator._repair(results, input_tasks)

    assert len(repaired) == 2
    # t1 should have both styles
    t1 = next(r for r in repaired if r["task_id"] == "t1")
    assert "formal" in t1["captions"]
    assert "sarcastic" in t1["captions"]
    # t2 should be created
    t2 = next(r for r in repaired if r["task_id"] == "t2")
    assert "formal" in t2["captions"]


def test_validate_and_write_atomic():
    """Should write valid results atomically."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal"]}]
    results = [{"task_id": "t1", "captions": {"formal": "A valid caption."}}]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "results.json")
        success = validator.validate_and_write(results, input_tasks, output_path)
        assert success is True
        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["task_id"] == "t1"
        assert data[0]["captions"]["formal"] == "A valid caption."


def test_validate_and_write_repairs():
    """Should repair and write when validation fails."""
    validator = OutputValidator()
    input_tasks = [{"task_id": "t1", "styles": ["formal", "sarcastic"]}]
    results = [{"task_id": "t1", "captions": {"formal": "ok"}}]  # missing sarcastic

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "results.json")
        success = validator.validate_and_write(results, input_tasks, output_path)
        assert success is True
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "sarcastic" in data[0]["captions"]