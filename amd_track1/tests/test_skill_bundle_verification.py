"""Verification tests for the AMD Track 1 skill bundle lane."""

import json
import sys

from amd_track1.classifier import TaskClassifier
from amd_track1.executor import FireworksClient, TaskExecutor
from amd_track1.model_registry import ModelRegistry
from amd_track1.prompt_builder import PromptBuilder
from amd_track1.router import RoutingDecision, TaskRouter
from amd_track1.tools.submission_validator import SubmissionValidator


def test_skills_drive_prompt_contract(skills_dir):
    classifier = TaskClassifier(skills_dir)
    prompt_builder = PromptBuilder(skills_dir)

    classification = classifier.classify(
        "task-1",
        "What is the capital of France?",
    )
    prompt_info = prompt_builder.build_prompt(
        "task-1",
        "What is the capital of France?",
        classification["category"],
    )

    assert classification["selected_skill"] == "factual_knowledge"
    assert prompt_info["prompt"] == "What is the capital of France?"
    assert prompt_info["output_shape"] == "string"


def test_math_deterministic_path_uses_zero_model_calls(skills_dir):
    executor = TaskExecutor(skills_dir=skills_dir)
    executor._registry = ModelRegistry()
    executor._registry.initialize("fireworks-model")
    executor._router._registry = executor._registry

    class FailingModelClient:
        def infer(self, *args, **kwargs):
            raise AssertionError("model inference should not be called")

        @staticmethod
        def is_transient_error(error):
            return False

    executor._fireworks_client = FailingModelClient()

    result = executor.execute_task(
        {"task_id": "math-1", "prompt": "Calculate: 2 + 3"}
    )

    assert result.success is True
    assert result.answer == "5"
    assert result.model_used is None
    assert result.attempt_count == 1


def test_math_deterministic_path_handles_richer_expressions(skills_dir):
    executor = TaskExecutor(skills_dir=skills_dir)
    executor._registry = ModelRegistry()
    executor._registry.initialize("fireworks-model")
    executor._router._registry = executor._registry

    class FailingModelClient:
        def infer(self, *args, **kwargs):
            raise AssertionError("model inference should not be called")

        @staticmethod
        def is_transient_error(error):
            return False

    executor._fireworks_client = FailingModelClient()

    cases = [
        ("multi-op", "Calculate: 15 + 27 * 2", "69"),
        ("parentheses", "Calculate: (2 + 3) * 4", "20"),
        ("percentage", "What is 20% of 150?", "30"),
    ]

    for suffix, prompt, expected in cases:
        result = executor.execute_task({"task_id": f"math-{suffix}", "prompt": prompt})
        assert result.success is True
        assert result.answer == expected
        assert result.model_used is None
        assert result.attempt_count == 1


def test_arithmetic_evaluator_failure_falls_back_to_fireworks(monkeypatch, skills_dir):
    executor = TaskExecutor(skills_dir=skills_dir)
    executor._registry = ModelRegistry()
    executor._registry.initialize("fireworks-model")

    executor._router.route_task = lambda task: RoutingDecision(
        task_id=task["task_id"],
        category="mathematical_reasoning",
        selected_model=None,
        routing_reason="Deterministic tool arithmetic_evaluator can fully solve",
        validation_strategy="arithmetic_evaluator_validation",
        attempt_count=0,
        input_tokens=None,
        output_tokens=None,
        latency=None,
        escalation_reason=None,
    )

    def broken_extract(prompt):
        raise ValueError("broken calculator")

    monkeypatch.setattr("amd_track1.arithmetic_detection.extract_arithmetic_expression", broken_extract)

    class FireworksStub:
        def infer(self, *args, **kwargs):
            return ("5", None, 10, 1, 0.01)

        @staticmethod
        def is_transient_error(error):
            return False

    executor._fireworks_client = FireworksStub()

    result = executor.execute_task({"task_id": "math-fallback", "prompt": "Calculate: 2 + 3"})

    assert result.success is True
    assert result.answer == "5"
    assert result.model_used == "fireworks-model"


def test_factual_task_routes_to_fireworks_when_no_tool_can_solve(skills_dir):
    router = TaskRouter(skills_dir)
    router._registry = ModelRegistry()
    router._registry.initialize("fireworks-model")

    decision = router.route_task(
        {"task_id": "fact-1", "prompt": "What is the capital of France?"}
    )

    assert decision.category == "factual_knowledge"
    assert decision.selected_model == "fireworks-model"
    assert "tool" not in decision.routing_reason.lower()


def test_results_json_exact_contract_and_coverage():
    validator = SubmissionValidator()
    input_tasks = [
        {"task_id": "task-1", "prompt": "first"},
        {"task_id": "task-2", "prompt": "second"},
    ]
    raw_results = [
        {"task_id": "task-1", "answer": 42, "extra": "removed"},
        {"task_id": "task-2", "answer": "done"},
    ]

    packed = json.loads(validator.create_valid_output(raw_results))
    valid, errors = validator.validate_results_json(packed, input_tasks)

    assert valid is True
    assert errors == []
    assert packed == [
        {"task_id": "task-1", "answer": "42"},
        {"task_id": "task-2", "answer": "done"},
    ]


def test_transient_retry_detection_is_separate_from_content_validation():
    for status_code in (429, 500, 502, 503, 504):
        assert FireworksClient.is_transient_error(f"HTTP {status_code}: retry")

    for status_code in (400, 401, 404, 422):
        assert not FireworksClient.is_transient_error(f"HTTP {status_code}: stop")


def test_amd_lane_does_not_import_a_flow_or_edge_backend():
    assert "a_flow" not in sys.modules
    assert "edge_backend" not in sys.modules
