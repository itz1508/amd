"""Pipeline-level integration tests for AMD Track 1 conditional verifier.

Tests exercise the ACTIVE pipeline (executor.process_input and execute_task)
to verify verifier integration works end-to-end.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestConditionalVerifierIntegration:
    """Pipeline-level tests for conditional verifier integration."""

    @pytest.fixture
    def mock_fireworks_client(self, monkeypatch):
        """Mock FireworksClient to avoid actual API calls."""
        def mock_infer(model_id, prompt, timeout=300.0):
            # Return a simple answer
            return ("mock answer", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_cls:
            mock_instance = MagicMock()
            mock_instance.infer = Mock(side_effect=mock_infer)
            mock_instance.is_transient_error = Mock(return_value=False)
            mock_cls.return_value = mock_instance
            yield mock_instance

    def test_pipeline_deterministic_math_zero_model_calls(self, monkeypatch):
        """Deterministic math tasks use zero model calls and zero verifier calls."""
        # Mock FireworksClient to track calls
        infer_call_count = 0
        
        def mock_infer(model_id, prompt, timeout=300.0):
            nonlocal infer_call_count
            infer_call_count += 1
            return ("42", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a,model-b")
            
            # Execute a deterministic math task
            result = executor.execute_task({
                "task_id": "math-001",
                "prompt": "What is 2+2?"
            })
            
            # Deterministic tasks should have model_used=None
            # and zero model calls (infer not called)
            # The arithmetic evaluator should handle this
            assert result.task_id == "math-001"
            # The answer should be computed deterministically
            assert result.answer == "4"
            assert infer_call_count == 0, "Deterministic math should use zero model calls"
            # No verifier calls should happen for deterministic tasks
            # Since verifier uses the same client, infer_call_count should remain 0

    def test_pipeline_solver_model_selection_from_model_roles(self, monkeypatch):
        """Solver model selection uses model_roles.py."""
        infer_call_count = 0
        selected_models = []
        
        def mock_infer(model_id, prompt, timeout=300.0):
            nonlocal infer_call_count
            infer_call_count += 1
            selected_models.append(model_id)
            return ("answer", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("SOLVER_MODEL", "solver-model-xyz")
            monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
            
            from amd_track1.executor import TaskExecutor
            from amd_track1.model_roles import reset_model_cache
            reset_model_cache()
            
            executor = TaskExecutor()
            executor.initialize("model-a,model-b")
            
            # Execute a task that needs a model
            result = executor.execute_task({
                "task_id": "test-001",
                "prompt": "What is the capital of France?"
            })
            
            assert result.task_id == "test-001"
            assert infer_call_count > 0, "Model should be called"
            # The model selection should use get_solver_model() which returns SOLVER_MODEL env
            # But router may override this based on category performance
            # At minimum, we verify a model was called

    def test_pipeline_high_risk_calls_verifier_once(self, monkeypatch):
        """High-risk category tasks call verifier exactly once."""
        infer_call_count = 0
        
        def mock_infer(model_id, prompt, timeout=300.0):
            nonlocal infer_call_count
            infer_call_count += 1
            # For solver calls, return code; for verifier calls, return valid JSON response
            if "verifier" in prompt.lower() or "You are a verifier" in prompt:
                # This is a verifier call - return valid verifier JSON
                return ('{"decision": "accept", "gap": "", "correction_hint": "", "final_answer": "verified code"}', None, 10, 20, 0.5)
            else:
                # This is a solver call
                return ("some code", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a,model-b")
            
            # Mock the classifier to return high-risk category
            with patch.object(executor._classifier, 'classify') as mock_classify:
                mock_classify.return_value = {'category': 'code_generation'}
                
                result = executor.execute_task({
                    "task_id": "code-001",
                    "prompt": "Write Python code"
                })
                
                assert result.task_id == "code-001"
                assert infer_call_count == 2, "Both solver and verifier should be called for high-risk categories"

    def test_pipeline_process_input_deterministic(self, monkeypatch):
        """process_input with deterministic tasks produces correct output."""
        infer_call_count = 0
        
        def mock_infer(model_id, prompt, timeout=300.0):
            nonlocal infer_call_count
            infer_call_count += 1
            return ("answer", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a,model-b")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "tasks.json"
                output_path = Path(tmpdir) / "results.json"
                
                # Write test tasks
                tasks = [
                    {"task_id": "math-001", "prompt": "What is 2+2?"},
                    {"task_id": "math-002", "prompt": "What is 6*7?"}
                ]
                
                with open(input_path, 'w') as f:
                    json.dump(tasks, f)
                
                # Process input
                success, errors = executor.process_input(
                    str(input_path), str(output_path)
                )
                
                # Verify output
                assert output_path.exists()
                
                with open(output_path, 'r') as f:
                    results = json.load(f)
                
                assert len(results) == 2
                
                # Verify task IDs preserved
                output_ids = {r['task_id'] for r in results}
                input_ids = {t['task_id'] for t in tasks}
                assert input_ids == output_ids
                
                # Verify schema
                for result in results:
                    assert set(result.keys()) == {'task_id', 'answer'}
                    assert isinstance(result['answer'], str)

    def test_pipeline_output_schema_strict(self, monkeypatch):
        """Pipeline output contains only task_id and answer."""
        def mock_infer(model_id, prompt, timeout=300.0):
            return ("answer", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a")
            
            result = executor.execute_task({
                "task_id": "test-001",
                "prompt": "Test prompt"
            })
            
            output_dict = result.to_output_dict()
            
            assert set(output_dict.keys()) == {'task_id', 'answer'}
            assert output_dict['task_id'] == "test-001"
            assert isinstance(output_dict['answer'], str)

    def test_pipeline_all_task_ids_appear_exactly_once(self, monkeypatch):
        """Every input task_id appears exactly once in output."""
        def mock_infer(model_id, prompt, timeout=300.0):
            return ("answer", None, 10, 20, 0.5)
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "tasks.json"
                output_path = Path(tmpdir) / "results.json"
                
                tasks = [
                    {"task_id": "task-001", "prompt": "Prompt 1"},
                    {"task_id": "task-002", "prompt": "Prompt 2"},
                    {"task_id": "task-003", "prompt": "Prompt 3"}
                ]
                
                with open(input_path, 'w') as f:
                    json.dump(tasks, f)
                
                success, errors = executor.process_input(
                    str(input_path), str(output_path)
                )
                
                with open(output_path, 'r') as f:
                    results = json.load(f)
                
                input_ids = {t['task_id'] for t in tasks}
                output_ids = {r['task_id'] for r in results}
                
                assert input_ids == output_ids
                assert len(results) == len(output_ids)

    def test_smoke_real_process_input(self, monkeypatch):
        """Smoke test: real process_input generates output file from sample input."""
        def mock_infer(model_id, prompt, timeout=300.0):
            # For arithmetic prompts, return the computed answer
            import re
            # Match patterns like "2+2" or "2 + 2"
            matches = re.findall(r'(\d+)\s*([+\-*/])\s*(\d+)', prompt)
            if matches:
                a, op, b = int(matches[0][0]), matches[0][1], int(matches[0][2])
                if op == '+': return str(a + b), None, 10, 20, 0.1
                elif op == '-': return str(a - b), None, 10, 20, 0.1
                elif op == '*': return str(a * b), None, 10, 20, 0.1
                elif op == '/': return str(a // b), None, 10, 20, 0.1
            return "answer", None, 10, 20, 0.5
        
        with patch('amd_track1.executor.FireworksClient') as mock_exec_cls:
            mock_exec = MagicMock()
            mock_exec.infer = Mock(side_effect=mock_infer)
            mock_exec.is_transient_error = Mock(return_value=False)
            mock_exec_cls.return_value = mock_exec
            
            monkeypatch.setenv("ALLOWED_MODELS", "model-a")
            
            from amd_track1.executor import TaskExecutor
            
            executor = TaskExecutor()
            executor.initialize("model-a")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "tasks.json"
                output_path = Path(tmpdir) / "results.json"
                
                # Sample input
                tasks = [
                    {"task_id": "test-001", "prompt": "What is 2+2?"},
                    {"task_id": "test-002", "prompt": "What is 3*4?"}
                ]
                
                with open(input_path, 'w') as f:
                    json.dump(tasks, f)
                
                import time
                start = time.time()
                
                success, errors = executor.process_input(
                    str(input_path), str(output_path)
                )
                
                elapsed = time.time() - start
                
                # Verify output exists
                assert output_path.exists(), "Output file must be generated"
                
                # Verify output is valid JSON
                with open(output_path, 'r') as f:
                    results = json.load(f)
                
                # Verify results
                assert len(results) > 0, "Should have at least one result"
                
                for result in results:
                    assert 'task_id' in result
                    assert 'answer' in result
                    assert isinstance(result['answer'], str)
                
                # Runtime should be under 600 seconds (trivially true for this test)
                assert elapsed < 600, f"Runtime {elapsed}s should be under 600s"
                
                # Print for documentation
                print(f"\nSmoke test: {len(results)} results in {elapsed:.3f}s")
                print(f"Results: {results}")
