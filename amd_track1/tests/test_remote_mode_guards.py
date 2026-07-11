"""Guard tests for Fireworks-only model selection and allowed-model handling."""

from unittest.mock import patch


class TestRemoteModeIgnored:
    """Legacy AMD_REMOTE_MODE values must not re-enable local inference."""

    def test_off_does_not_block_fireworks_in_v3(self, monkeypatch):
        monkeypatch.setenv("AMD_REMOTE_MODE", "off")

        from amd_track1.executor import TaskExecutor

        executor = TaskExecutor(
            api_key="test-key",
            base_url="https://api.fireworks.ai",
        )

        assert executor._select_inference_client("any-model") is executor._fireworks_client

    def test_rescue_does_not_prefer_local_in_v3(self, monkeypatch):
        monkeypatch.setenv("AMD_REMOTE_MODE", "rescue")
        monkeypatch.setenv("LOCAL_MODEL_URL", "http://127.0.0.1:8080")
        monkeypatch.setenv("LOCAL_MODEL_ID", "local-qwen")

        from amd_track1.executor import TaskExecutor
        from amd_track1.local_client import LocalInferenceClient

        local_client = LocalInferenceClient()
        executor = TaskExecutor(
            local_client=local_client,
            api_key="test-key",
            base_url="https://api.fireworks.ai",
        )

        assert executor._local_client is None
        assert executor._select_inference_client("local-qwen") is executor._fireworks_client


class TestAllowedModelsRuntimeOnly:
    """Remote model IDs must come from ALLOWED_MODELS only."""

    def test_solver_from_allowed_models(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
        from amd_track1.model_roles import get_solver_model, reset_model_cache

        reset_model_cache()
        assert get_solver_model() == "model-a"

    def test_verifier_from_allowed_models(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_MODELS", "model-a,model-b")
        from amd_track1.model_roles import get_verifier_model, reset_model_cache

        reset_model_cache()
        assert get_verifier_model() == "model-b"

    def test_no_hardcoded_model_ids(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_MODELS", "custom-model-1,custom-model-2")
        from amd_track1.model_roles import get_solver_model, get_verifier_model, reset_model_cache

        reset_model_cache()
        assert get_solver_model() in ("custom-model-1", "custom-model-2")
        assert get_verifier_model() in ("custom-model-1", "custom-model-2")

    def test_empty_allowed_models_returns_none(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_MODELS", "")
        from amd_track1.model_roles import get_solver_model, reset_model_cache

        reset_model_cache()
        assert get_solver_model() is None

    def test_missing_allowed_models_returns_none(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_MODELS", raising=False)
        from amd_track1.model_roles import get_solver_model, reset_model_cache

        reset_model_cache()
        assert get_solver_model() is None


class TestLocalQwenIsolation:
    """local-qwen must not be selected as a Fireworks model by the router."""

    def test_router_never_selects_local_qwen_for_remote(self):
        from amd_track1.model_registry import get_model_registry
        from amd_track1.router import TaskRouter

        registry = get_model_registry()
        registry._models.clear()
        registry._initialized = False
        registry.initialize("remote-model-1,local-qwen")

        router = TaskRouter()
        router._registry = registry

        decision = router.route_task(
            {"task_id": "t1", "prompt": "Write a Python function"}
        )

        assert decision.selected_model == "remote-model-1"

    def test_fireworks_client_sends_requested_model(self):
        from amd_track1.executor import FireworksClient

        client = FireworksClient(api_key="test-key", base_url="https://api.fireworks.ai")
        captured_payloads = []

        def capture_post(url, headers, json, timeout):
            class FakeResponse:
                status_code = 200

                def json(self):
                    return {
                        "choices": [{"message": {"content": "ok"}}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                    }

            captured_payloads.append(json)
            return FakeResponse()

        with patch("requests.post", side_effect=capture_post):
            client.infer("remote-model-1", "test prompt")

        assert captured_payloads[0]["model"] == "remote-model-1"


class TestEntrypointLocalModeWiring:
    """get_executor must not wire local clients in production v3."""

    def test_get_executor_ignores_local_env(self, monkeypatch):
        monkeypatch.setenv("LOCAL_MODEL_URL", "http://127.0.0.1:8080")
        monkeypatch.setenv("LOCAL_MODEL_ID", "local-qwen")
        monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
        monkeypatch.delenv("FIREWORKS_BASE_URL", raising=False)

        import amd_track1.executor as executor_mod
        from amd_track1.executor import get_executor

        executor_mod._executor_instance = None
        executor = get_executor()

        assert executor._local_client is None

        executor_mod._executor_instance = None
