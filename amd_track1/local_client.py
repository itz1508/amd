"""
Local inference client for AMD Track 1.

Wraps llama.cpp server (or any OpenAI-compatible local endpoint) so that
the existing FireworksClient can be reused by swapping the base_url.
No Ollama dependency.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


class LocalInferenceClient:
    """Client for local inference via an OpenAI-compatible endpoint."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize local inference client.

        Args:
            base_url: URL of the local OpenAI-compatible server
                     (default: LOCAL_MODEL_URL env var, or http://127.0.0.1:8080)
            model_id: Model ID to use for local inference
                     (default: LOCAL_MODEL_ID env var, or "local-qwen")
            api_key: Optional API key (local servers usually ignore this)
        """
        self.base_url = (
            base_url
            or os.environ.get("LOCAL_MODEL_URL", "http://127.0.0.1:8080")
        ).rstrip("/")
        self.model_id = model_id or os.environ.get("LOCAL_MODEL_ID", "local-qwen")
        self.api_key = api_key or os.environ.get("LOCAL_MODEL_API_KEY", "no-key")
        self._fireworks_client: Optional[Any] = None
        self._server_process: Optional[subprocess.Popen] = None

    @property
    def fireworks_client(self) -> Any:
        """Lazy-initialize a FireworksClient pointing at the local server."""
        # Lazy import to avoid circular dependency: local_client → executor → router → local_client
        from .executor import FireworksClient

        if self._fireworks_client is None:
            self._fireworks_client = FireworksClient(
                api_key=self.api_key,
                base_url=self.base_url,
                max_transport_retries=2,
                transport_retry_base_delay=0.5,
                transport_retry_max_delay=5.0,
            )
        return self._fireworks_client

    def is_available(self, timeout: float = 5.0) -> bool:
        """Check if the local server is reachable."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/v1/models",
                method="GET",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def infer(
        self,
        prompt: str,
        timeout: float = 300.0,
    ) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int], Optional[float]]:
        """
        Run inference against the local model.

        Args:
            prompt: The prompt to send
            timeout: Timeout in seconds

        Returns:
            Tuple of (answer, error, input_tokens, output_tokens, latency)
        """
        return self.fireworks_client.infer(
            model_id=self.model_id,
            prompt=prompt,
            timeout=timeout,
        )

    def start_server(
        self,
        model_path: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        context_size: int = 4096,
        llama_server_path: Optional[str] = None,
    ) -> bool:
        """
        Start llama-server as a background process.

        Args:
            model_path: Path to the GGUF model file
                       (default: LOCAL_MODEL_PATH env var)
            host: Bind host
            port: Bind port
            context_size: Context size in tokens
            llama_server_path: Path to llama-server executable
                              (default: LLAMA_SERVER_PATH env var or PATH lookup)

        Returns:
            True if server started and is healthy
        """
        if self.is_available(timeout=2.0):
            return True  # Already running

        model_path = model_path or os.environ.get("LOCAL_MODEL_PATH")
        if not model_path:
            return False

        llama_server_path = llama_server_path or os.environ.get(
            "LLAMA_SERVER_PATH", "llama-server"
        )

        cmd = [
            llama_server_path,
            "-m", model_path,
            "--host", host,
            "--port", str(port),
            "-c", str(context_size),
            "--no-webui",
        ]

        try:
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            return False

        # Wait for server to be ready
        deadline = time.time() + 60.0
        while time.time() < deadline:
            if self.is_available(timeout=1.0):
                return True
            if self._server_process.poll() is not None:
                # Process exited early
                return False
            time.sleep(0.5)

        return False

    def stop_server(self) -> None:
        """Stop the background server if we started it."""
        if self._server_process is not None:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
                self._server_process.wait()
            self._server_process = None


def get_local_client() -> Optional[LocalInferenceClient]:
    """
    Factory: return a LocalInferenceClient if local mode is configured.

    Returns None if LOCAL_MODEL_URL is not set and no server is expected.
    """
    if "LOCAL_MODEL_URL" in os.environ or "LOCAL_MODEL_PATH" in os.environ:
        return LocalInferenceClient()
    return None


def is_local_mode_enabled() -> bool:
    """Check whether local-first mode is enabled via environment."""
    return (
        "LOCAL_MODEL_URL" in os.environ
        or "LOCAL_MODEL_PATH" in os.environ
        or os.environ.get("LOCAL_FIRST", "").lower() in ("1", "true", "yes")
    )