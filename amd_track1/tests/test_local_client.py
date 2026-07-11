"""
Tests for LocalInferenceClient.
"""

import os
import pytest
import sys
import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

# Ensure amd_track1 is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLocalInferenceClient:
    """Tests for LocalInferenceClient class."""

    def test_init_defaults(self):
        """Local client requires explicit local endpoint configuration."""
        from amd_track1.local_client import LocalInferenceClient

        with pytest.raises(ValueError, match="LOCAL_MODEL_URL not set"):
            LocalInferenceClient()

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variables."""
        from amd_track1.local_client import LocalInferenceClient

        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:9999")
        monkeypatch.setenv("LOCAL_MODEL_ID", "test-model")
        monkeypatch.setenv("LOCAL_MODEL_API_KEY", "test-key")

        client = LocalInferenceClient()
        assert client.base_url == "http://localhost:9999"
        assert client.model_id == "test-model"
        assert client.api_key == "test-key"

    def test_init_override_env(self, monkeypatch):
        """Test that constructor parameters override env vars."""
        from amd_track1.local_client import LocalInferenceClient

        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:9999")
        monkeypatch.setenv("LOCAL_MODEL_ID", "env-model")
        client = LocalInferenceClient(base_url="http://override:8888")
        assert client.base_url == "http://override:8888"

    def test_fireworks_client_lazy_creation(self):
        """Test that fireworks_client is created lazily."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(base_url="http://localhost:8080", model_id="m", api_key="k")
        assert client._fireworks_client is None

        fw = client.fireworks_client
        assert client._fireworks_client is not None
        assert fw.base_url == "http://localhost:8080/v1"
        assert fw.api_key == "k"

    def test_is_available_success(self, monkeypatch):
        """Test is_available when server responds."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(
            base_url="http://localhost:8080",
            model_id="local-qwen",
        )

        # Mock urllib.request.urlopen to return a successful response
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        def fake_urlopen(req, timeout):
            return FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            assert client.is_available(timeout=1.0) is True

    def test_is_available_failure(self, monkeypatch):
        """Test is_available when server is down."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(
            base_url="http://localhost:8080",
            model_id="local-qwen",
        )

        def fake_urlopen(req, timeout):
            raise URLError("Connection refused")

        with patch("urllib.request.urlopen", fake_urlopen):
            assert client.is_available(timeout=1.0) is False

    def test_infer_delegates_to_fireworks(self, monkeypatch):
        """Test that infer delegates to the FireworksClient."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(
            base_url="http://localhost:8080",
            model_id="my-model",
        )

        # Mock the underlying _fireworks_client directly (property has no setter)
        mock_fw = MagicMock()
        mock_fw.infer.return_value = ("answer", None, 10, 5, 1.0)
        client._fireworks_client = mock_fw

        result = client.infer("test prompt", timeout=30.0)
        mock_fw.infer.assert_called_once_with(
            model_id="my-model",
            prompt="test prompt",
            timeout=30.0,
        )
        assert result == ("answer", None, 10, 5, 1.0)

    def test_start_server_no_model_path(self):
        """Test start_server fails without model path."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(
            base_url="http://localhost:8080",
            model_id="local-qwen",
        )
        with patch.object(client, "is_available", return_value=False):
            assert client.start_server() is False

    def test_stop_server_not_started(self):
        """Test stop_server when no server was started."""
        from amd_track1.local_client import LocalInferenceClient

        client = LocalInferenceClient(
            base_url="http://localhost:8080",
            model_id="local-qwen",
        )
        # Should not raise
        client.stop_server()
        assert client._server_process is None


class TestLocalClientFactories:
    """Tests for factory functions."""

    def test_get_local_client_with_url(self, monkeypatch):
        """Test get_local_client returns client when LOCAL_MODEL_URL is set."""
        from amd_track1.local_client import get_local_client

        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:8080")
        monkeypatch.setenv("LOCAL_MODEL_ID", "local-qwen")
        client = get_local_client()
        assert client is not None
        assert client.base_url == "http://localhost:8080"

    def test_get_local_client_with_path(self, monkeypatch):
        """Test get_local_client returns client when LOCAL_MODEL_PATH is set."""
        from amd_track1.local_client import get_local_client

        monkeypatch.setenv("LOCAL_MODEL_PATH", "/path/to/model.gguf")
        with pytest.raises(ValueError, match="LOCAL_MODEL_URL not set"):
            get_local_client()

    def test_get_local_client_none(self, monkeypatch):
        """Test get_local_client returns None when no local config."""
        from amd_track1.local_client import get_local_client

        monkeypatch.delenv("LOCAL_MODEL_URL", raising=False)
        monkeypatch.delenv("LOCAL_MODEL_PATH", raising=False)
        client = get_local_client()
        assert client is None

    def test_is_local_mode_enabled_url(self, monkeypatch):
        """Test is_local_mode_enabled with LOCAL_MODEL_URL."""
        from amd_track1.local_client import is_local_mode_enabled

        monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:8080")
        monkeypatch.delenv("LOCAL_FIRST", raising=False)
        assert is_local_mode_enabled() is True

    def test_is_local_mode_enabled_path(self, monkeypatch):
        """Test is_local_mode_enabled with LOCAL_MODEL_PATH."""
        from amd_track1.local_client import is_local_mode_enabled

        monkeypatch.setenv("LOCAL_MODEL_PATH", "/path/to/model.gguf")
        monkeypatch.delenv("LOCAL_FIRST", raising=False)
        assert is_local_mode_enabled() is True

    def test_is_local_mode_enabled_flag(self, monkeypatch):
        """Test is_local_mode_enabled with LOCAL_FIRST flag."""
        from amd_track1.local_client import is_local_mode_enabled

        monkeypatch.delenv("LOCAL_MODEL_URL", raising=False)
        monkeypatch.delenv("LOCAL_MODEL_PATH", raising=False)
        monkeypatch.setenv("LOCAL_FIRST", "true")
        assert is_local_mode_enabled() is True

    def test_is_local_mode_disabled(self, monkeypatch):
        """Test is_local_mode_enabled returns False when nothing set."""
        from amd_track1.local_client import is_local_mode_enabled

        monkeypatch.delenv("LOCAL_MODEL_URL", raising=False)
        monkeypatch.delenv("LOCAL_MODEL_PATH", raising=False)
        monkeypatch.setenv("LOCAL_FIRST", "false")
        assert is_local_mode_enabled() is False
