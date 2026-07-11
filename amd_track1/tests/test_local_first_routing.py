"""Guard tests for the v3 no-local-inference production route."""

from unittest.mock import MagicMock


class TestRouterFireworksOnly:
    """Router must never prefer local models for non-deterministic work."""

    def test_sentiment_routes_to_fireworks_model_even_when_local_registered(self):
        from amd_track1.model_registry import get_model_registry
        from amd_track1.router import TaskRouter

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("remote-model-1,remote-model-2,local-qwen")

        router = TaskRouter()
        router._registry = registry
        router._classifier = MagicMock()
        router._classifier.classify.return_value = {"category": "sentiment_classification"}

        decision = router.route_task({"task_id": "t1", "prompt": "I love this product!"})

        assert decision.selected_model == "remote-model-1"
        assert "Local-first" not in decision.routing_reason

    def test_code_generation_routes_to_fireworks_model(self):
        from amd_track1.model_registry import get_model_registry
        from amd_track1.router import TaskRouter

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("remote-model-1,local-qwen")

        router = TaskRouter()
        router._registry = registry

        decision = router.route_task(
            {"task_id": "t2", "prompt": "Write a Python function to sort a list"}
        )

        assert decision.selected_model == "remote-model-1"

    def test_deterministic_math_uses_tool_route(self):
        from amd_track1.model_registry import get_model_registry
        from amd_track1.router import TaskRouter

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("remote-model-1")

        router = TaskRouter()
        router._registry = registry

        decision = router.route_task({"task_id": "t3", "prompt": "Calculate: 15 + 27 * 2"})

        assert decision.selected_model is None
        assert "Deterministic tool arithmetic_evaluator" in decision.routing_reason


class TestExecutorFireworksOnly:
    """TaskExecutor ignores local clients in production v3."""

    def test_select_inference_client_uses_fireworks_when_configured(self, monkeypatch):
        from amd_track1.executor import TaskExecutor
        from amd_track1.local_client import LocalInferenceClient

        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:8080")
        monkeypatch.setenv("LOCAL_MODEL_ID", "local-qwen")

        local_client = LocalInferenceClient()
        executor = TaskExecutor(
            local_client=local_client,
            api_key="test-key",
            base_url="https://api.fireworks.ai",
        )

        assert executor._local_client is None
        assert executor._select_inference_client("local-qwen") is executor._fireworks_client

    def test_select_inference_client_none_available(self):
        from amd_track1.executor import TaskExecutor

        executor = TaskExecutor()

        assert executor._select_inference_client("any-model") is None
