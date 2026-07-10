"""
Tests for structural I/O behavior under local-first mode.
Validates S3 edge: missing local model degrades cleanly, still writes valid /output/results.json.
"""

import os
import pytest
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock

# Ensure amd_track1 is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStructuralIO:
    """Tests for structural input/output behavior."""

    def test_valid_input_output_cycle(self, tmp_path):
        """Full cycle: valid input produces valid output."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        # Create a temporary input file
        input_file = tmp_path / "tasks.json"
        input_data = [
            {"task_id": "task-1", "prompt": "What is 2 + 2?"},
            {"task_id": "task-2", "prompt": "Summarize: hello world"},
        ]
        input_file.write_text(json.dumps(input_data))

        output_file = tmp_path / "results.json"

        # Initialize registry with a dummy model
        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("dummy-model")

        # Create executor with mocked client to avoid network calls
        executor = TaskExecutor(api_key="test", base_url="http://test")
        executor._fireworks_client = MagicMock()
        executor._fireworks_client.infer.return_value = ("4", None, 10, 5, 1.0)

        # Patch category validator to always pass so mocked answers succeed
        with patch.object(executor._category_validator, "validate", return_value=(True, [])):
            success, errors = executor.process_input(
                str(input_file), str(output_file), total_timeout=60.0
            )

        assert success is True
        assert len(errors) == 0
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert isinstance(output_data, list)
        assert len(output_data) == 2
        assert all("task_id" in r for r in output_data)
        assert all("answer" in r for r in output_data)

    def test_malformed_input_skips_bad_records(self, tmp_path):
        """Malformed records are skipped, valid ones still processed."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        input_file = tmp_path / "tasks.json"
        input_data = [
            {"task_id": "valid-1", "prompt": "What is 2 + 2?"},
            {"invalid": "no task_id"},
            {"task_id": "valid-2", "prompt": "Summarize: hello"},
        ]
        input_file.write_text(json.dumps(input_data))

        output_file = tmp_path / "results.json"

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("dummy-model")

        executor = TaskExecutor(api_key="test", base_url="http://test")
        executor._fireworks_client = MagicMock()
        executor._fireworks_client.infer.return_value = ("answer", None, 10, 5, 1.0)

        # Patch category validator to always pass so mocked answers succeed
        with patch.object(executor._category_validator, "validate", return_value=(True, [])):
            success, errors = executor.process_input(
                str(input_file), str(output_file), total_timeout=60.0
            )

        # Should succeed with warnings about malformed records
        assert output_file.exists()
        output_data = json.loads(output_file.read_text())
        assert isinstance(output_data, list)
        # At least the valid tasks should be present
        task_ids = {r["task_id"] for r in output_data}
        assert "valid-1" in task_ids or "valid-2" in task_ids

    def test_empty_input_writes_empty_array(self, tmp_path):
        """Empty input produces empty output array."""
        from amd_track1.executor import TaskExecutor

        input_file = tmp_path / "tasks.json"
        input_file.write_text("[]")

        output_file = tmp_path / "results.json"

        executor = TaskExecutor(api_key="test", base_url="http://test")
        success, errors = executor.process_input(
            str(input_file), str(output_file), total_timeout=60.0
        )

        assert success is True
        assert output_file.exists()
        output_data = json.loads(output_file.read_text())
        assert output_data == []

    def test_output_schema_compliance(self, tmp_path):
        """Output conforms to required schema: list of {task_id, answer}."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        input_file = tmp_path / "tasks.json"
        input_data = [{"task_id": "t1", "prompt": "Test"}]
        input_file.write_text(json.dumps(input_data))

        output_file = tmp_path / "results.json"

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("dummy-model")

        executor = TaskExecutor(api_key="test", base_url="http://test")
        executor._fireworks_client = MagicMock()
        executor._fireworks_client.infer.return_value = ("answer", None, 10, 5, 1.0)

        success, errors = executor.process_input(
            str(input_file), str(output_file), total_timeout=60.0
        )

        assert success is True
        output_data = json.loads(output_file.read_text())

        # Schema validation
        assert isinstance(output_data, list)
        for record in output_data:
            assert isinstance(record, dict)
            assert "task_id" in record
            assert "answer" in record
            assert isinstance(record["task_id"], str)
            assert isinstance(record["answer"], str)
            # No extra fields in output
            assert set(record.keys()) == {"task_id", "answer"}

    def test_missing_local_model_degrades_cleanly(self, monkeypatch, tmp_path):
        """S3 edge: missing local model still produces valid output via remote."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        # Configure local mode but server is unavailable
        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:9999")
        monkeypatch.setenv("LOCAL_MODEL_ID", "local-qwen")
        monkeypatch.setenv("FIREWORKS_API_KEY", "test-key")
        monkeypatch.setenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai")
        monkeypatch.setenv("ALLOWED_MODELS", "remote-model")

        input_file = tmp_path / "tasks.json"
        input_data = [{"task_id": "t1", "prompt": "What is 2 + 2?"}]
        input_file.write_text(json.dumps(input_data))

        output_file = tmp_path / "results.json"

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False

        executor = TaskExecutor(api_key="test-key", base_url="https://api.fireworks.ai")
        # Mock remote client
        executor._fireworks_client = MagicMock()
        executor._fireworks_client.infer.return_value = ("4", None, 10, 5, 1.0)

        success, errors = executor.process_input(
            str(input_file), str(output_file), total_timeout=60.0
        )

        # Should succeed using remote fallback
        assert success is True
        assert output_file.exists()
        output_data = json.loads(output_file.read_text())
        assert len(output_data) == 1
        assert output_data[0]["task_id"] == "t1"
        assert output_data[0]["answer"] == "4"

    def test_no_models_available_fails_gracefully(self, tmp_path):
        """When no models are available, process fails gracefully."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        input_file = tmp_path / "tasks.json"
        input_data = [{"task_id": "t1", "prompt": "Test"}]
        input_file.write_text(json.dumps(input_data))

        output_file = tmp_path / "results.json"

        # Clear registry so no models are available
        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        # Don't initialize - no models

        executor = TaskExecutor()
        # No local client, no fireworks client

        success, errors = executor.process_input(
            str(input_file), str(output_file), total_timeout=60.0
        )

        # Should fail but not crash
        assert success is False
        assert len(errors) > 0

    def test_atomic_write_creates_output_dir(self, tmp_path):
        """Output directory is created if it doesn't exist."""
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_registry import get_model_registry

        input_file = tmp_path / "tasks.json"
        input_data = [{"task_id": "t1", "prompt": "Test"}]
        input_file.write_text(json.dumps(input_data))

        # Nested output path that doesn't exist yet
        output_file = tmp_path / "nested" / "deep" / "results.json"

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("dummy-model")

        executor = TaskExecutor(api_key="test", base_url="http://test")
        executor._fireworks_client = MagicMock()
        executor._fireworks_client.infer.return_value = ("answer", None, 10, 5, 1.0)

        success, errors = executor.process_input(
            str(input_file), str(output_file), total_timeout=60.0
        )

        assert success is True
        assert output_file.exists()