"""OpenAI-compatible vision client with base64 image encoding and JSON mode."""

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from amd_track2.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 2


class VisionConfigurationError(Exception):
    """Raised when vision client configuration is invalid."""
    pass


@dataclass(frozen=True)
class VisionResponse:
    """Structured response from vision model."""

    success: bool
    content: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    usage_prompt_tokens: Optional[int] = None
    usage_completion_tokens: Optional[int] = None
    http_status: Optional[int] = None
    request_id: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class VisionCallMetadata:
    """Metadata about a vision API call for evidence packet."""
    http_status: Optional[int] = None
    request_id: Optional[str] = None
    model: Optional[str] = None
    attempts: int = 0
    error_code: Optional[str] = None


def classify_vision_error(status_code: Optional[int], error_message: str) -> str:
    """Classify vision API error into specific error codes.

    Returns stable error code for evidence packet.
    """
    if status_code is None:
        return "network_error"

    if status_code == 401:
        return "missing_credential"
    if status_code == 403:
        return "permission_denied"
    if status_code == 404:
        return "unsupported_model"
    if status_code == 429:
        return "quota_restriction"
    if status_code >= 500:
        return "provider_error"
    if status_code >= 400:
        return "invalid_request"

    return "unknown_error"


class VisionClient:
    """OpenAI-compatible vision API client supporting base64 images."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.api_key = api_key or os.environ.get("FIREWORKS_API_KEY", "")
        self.base_url = (base_url or os.environ.get("FIREWORKS_BASE_URL", "")).rstrip(
            "/ "
        )
        allowed = [m.strip() for m in os.environ.get("ALLOWED_MODELS", "").split(",") if m.strip()]
        self.model = model or (allowed[0] if allowed else "")
        self.timeout = timeout_seconds
        self.max_retries = max_retries

        # Validate configuration early
        self._validate_config()

        self.retry = RetryPolicy(
            max_attempts=max_retries,
            base_delay_seconds=2.0,
            deadline_seconds=timeout_seconds * 2,
            retryable_exceptions=(requests.RequestException, TimeoutError, OSError),
        )

    def _validate_config(self) -> None:
        """Validate vision client configuration. Does not raise for retryable cases."""
        # Missing API key is logged but not fatal (may work with some providers)
        if not self.api_key:
            logger.warning("FIREWORKS_API_KEY not set")

        # Missing base URL is logged; no alternate provider is selected.
        if not self.base_url:
            logger.warning("FIREWORKS_BASE_URL not set")

        logger.debug(
            "VisionClient configured: model=%s, base_url=%s",
            self.model,
            self.base_url or "unset",
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _endpoint(self) -> str:
        if not self.base_url:
            return ""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    @staticmethod
    def _encode_image(image_path: str) -> str:
        """Read image and return base64 data URI."""
        with open(image_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    def _build_content(
        self, text: str, image_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """Build OpenAI vision message content with text and images."""
        content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
        for path in image_paths:
            if os.path.exists(path):
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": self._encode_image(path)},
                    }
                )
            else:
                logger.warning("Image path missing, skipping: %s", path)
        return content

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str],
        response_format: Optional[Dict[str, str]] = None,
    ) -> VisionResponse:
        """Send one vision request and return parsed response."""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": self._build_content(user_prompt, image_paths),
            },
        ]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        if response_format:
            payload["response_format"] = response_format

        attempt_count = 0
        last_exception: Optional[Exception] = None
        last_http_status: Optional[int] = None
        last_request_id: Optional[str] = None
        last_error_code: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            attempt_count = attempt
            try:
                resp = requests.post(
                    self._endpoint(),
                    headers=self._headers(),
                    json=payload,
                    timeout=(10, self.timeout),
                )
                last_http_status = resp.status_code
                last_request_id = resp.headers.get("x-request-id") or resp.headers.get("x-amzn-RequestId")

                if resp.status_code != 200:
                    # Don't retry client errors (4xx except 429)
                    if 400 <= resp.status_code < 500 and resp.status_code != 429:
                        error_code = classify_vision_error(resp.status_code, resp.text)
                        return VisionResponse(
                            success=False,
                            error_message=f"Vision API returned {resp.status_code}: {resp.text[:200]}",
                            http_status=resp.status_code,
                            request_id=last_request_id,
                            error_code=error_code,
                        )

                    # Retry server errors and 429
                    if attempt < self.max_retries:
                        delay = min(2.0 * (2 ** (attempt - 1)), 30.0)
                        logger.warning(
                            "Attempt %d/%d failed: HTTP %s. Retrying in %.1fs",
                            attempt,
                            self.max_retries,
                            resp.status_code,
                            delay,
                        )
                        last_error_code = classify_vision_error(resp.status_code, resp.text)
                        last_exception = Exception(f"HTTP {resp.status_code}")
                        continue

                    error_code = classify_vision_error(resp.status_code, resp.text)
                    return VisionResponse(
                        success=False,
                        error_message=f"Vision API failed after {attempt} attempts: HTTP {resp.status_code}",
                        http_status=resp.status_code,
                        request_id=last_request_id,
                        error_code=error_code,
                    )

                data = resp.json()

                usage = data.get("usage", {})
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                raw_content = message.get("content", "")

                parsed: Optional[Dict[str, Any]] = None
                if response_format and response_format.get("type") == "json_object":
                    try:
                        parsed = json.loads(raw_content)
                    except json.JSONDecodeError as exc:
                        logger.warning("Failed to parse JSON response: %s", exc)
                else:
                    parsed = self._extract_json(raw_content)

                return VisionResponse(
                    success=True,
                    content=raw_content,
                    parsed_json=parsed,
                    usage_prompt_tokens=usage.get("prompt_tokens"),
                    usage_completion_tokens=usage.get("completion_tokens"),
                    http_status=200,
                    request_id=last_request_id,
                )

            except requests.RequestException as exc:
                last_exception = exc
                last_error_code = classify_vision_error(None, str(exc))
                if attempt < self.max_retries:
                    delay = min(2.0 * (2 ** (attempt - 1)), 30.0)
                    logger.warning(
                        "Request attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt,
                        self.max_retries,
                        exc,
                        delay,
                    )
                else:
                    logger.error("All vision request attempts failed: %s", exc)

            except Exception as exc:
                logger.exception("Vision API unexpected error")
                return VisionResponse(
                    success=False,
                    error_message=f"Vision API error: {exc}",
                    error_code="unexpected_error",
                )

        # All retries exhausted
        return VisionResponse(
            success=False,
            error_message=f"Vision API error after {attempt_count} attempts: {last_exception}",
            http_status=last_http_status,
            request_id=last_request_id,
            error_code=last_error_code or "network_error",
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Try to find and parse JSON object from text."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass

        # Try first { ... } block
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        return None
