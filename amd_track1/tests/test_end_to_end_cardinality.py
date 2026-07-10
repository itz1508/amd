"""End-to-end cardinality tests for AMD Track 1.

Verify that input tasks and output results have exact 1:1 correspondence.
"""

import json
import tempfile
from pathlib import Path
import pytest


class TestEndToEndCardinality:
    """End-to-end tests verifying input/output cardinality."""

    def test_input_output_cardinality_exact_match(self, monkeypatch):
        """Input task count must equal output result count."""
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
        
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_roles import reset_model_cache
        reset_model_cache()
        
        executor = TaskExecutor()
        executor.initialize("model-a,model-b")
        
        # Create 3 deterministic math tasks
        input_tasks = [
            {"task_id": "card-001", "prompt": "What is 1+1?"},
            {"task_id": "card-002", "prompt": "What is 2+2?"},
            {"task_id": "card-003", "prompt": "What is 3+3?"},
        ]
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_tasks, f)
            input_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            # Process input
            success, errors = executor.process_input(
                input_path=input_path,
                output_path=output_path,
                total_timeout=10
            )
            
            assert success, f"Processing failed: {errors}"
            
            # Read output
            with open(output_path, 'r') as f:
                output_results = json.load(f)
            
            # Verify cardinality
            assert len(output_results) == len(input_tasks), \
                f"Output count ({len(output_results)}) != Input count ({len(input_tasks)})"
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_every_input_task_id_appears_exactly_once(self, monkeypatch):
        """Every input task_id must appear exactly once in output."""
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
        
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_roles import reset_model_cache
        reset_model_cache()
        
        executor = TaskExecutor()
        executor.initialize("model-a,model-b")
        
        input_tasks = [
            {"task_id": "e2e-001", "prompt": "What is 4+5?"},
            {"task_id": "e2e-002", "prompt": "What is 6+7?"},
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_tasks, f)
            input_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            success, errors = executor.process_input(
                input_path=input_path,
                output_path=output_path,
                total_timeout=10
            )
            
            assert success, f"Processing failed: {errors}"
            
            with open(output_path, 'r') as f:
                output_results = json.load(f)
            
            input_task_ids = {t["task_id"] for t in input_tasks}
            output_task_ids = {r["task_id"] for r in output_results}
            
            # Verify every input task_id appears exactly once
            assert input_task_ids == output_task_ids, \
                f"Task ID mismatch: input={input_task_ids}, output={output_task_ids}"
            
            # Verify no duplicates in output
            assert len(output_task_ids) == len(output_results), \
                "Duplicate task_id in output"
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_no_extra_output_task_ids(self, monkeypatch):
        """Output must not contain task_ids not in input."""
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
        
        from amd_track1.executor import TaskExecutor
        from amd_track1.model_roles import reset_model_cache
        reset_model_cache()
        
        executor = TaskExecutor()
        executor.initialize("model-a,model-b")
        
        input_tasks = [
            {"task_id": "extra-001", "prompt": "What is 10+10?"},
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_tasks, f)
            input_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            success, errors = executor.process_input(
                input_path=input_path,
                output_path=output_path,
                total_timeout=10
            )
            
            assert success, f"Processing failed: {errors}"
            
            with open(output_path, 'r') as f:
                output_results = json.load(f)
            
            input_task_ids = {t["task_id"] for t in input_tasks}
            output_task_ids = {r["task_id"] for r in output_results}
            
            # Verify no extra task_ids in output
            extra_ids = output_task_ids - input_task_ids
            assert not extra_ids, f"Extra task_ids in output: {extra_ids}"
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
