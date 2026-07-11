"""Download video from URL with bounded time/size and structured failure reporting."""

import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from amd_track2.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
DOWNLOAD_TIMEOUT_SECONDS = 120
DOWNLOAD_CHUNK_SIZE = 8192


@dataclass(frozen=True)
class FetchResult:
    """Structured result of a video fetch attempt."""

    success: bool
    local_path: Optional[str] = None
    source_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    file_size_bytes: Optional[int] = None
    download_seconds: Optional[float] = None


class VideoFetcher:
    """Fetch remote video into local temp storage with safety guards."""

    def __init__(
        self,
        max_size_bytes: int = MAX_FILE_SIZE_BYTES,
        timeout_seconds: int = DOWNLOAD_TIMEOUT_SECONDS,
        temp_dir: Optional[str] = None,
    ):
        self.max_size = max_size_bytes
        self.timeout = timeout_seconds
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.retry = RetryPolicy(
            max_attempts=2,
            base_delay_seconds=2.0,
            deadline_seconds=timeout_seconds * 2,
            retryable_exceptions=(requests.RequestException, OSError, TimeoutError),
        )

    def fetch(self, video_url: str, task_id: str) -> FetchResult:
        """Download video_url to a temp file. Returns FetchResult on success or failure."""
        if not video_url or not video_url.startswith(("http://", "https://")):
            return FetchResult(
                success=False,
                source_url=video_url,
                error_code="invalid_url",
                error_message="URL must be http or https",
            )

        parsed = urlparse(video_url)
        if not parsed.netloc:
            return FetchResult(
                success=False,
                source_url=video_url,
                error_code="invalid_url",
                error_message="URL missing host",
            )

        try:
            local_path = self._download(video_url, task_id)
            size = os.path.getsize(local_path)
            if size == 0:
                return FetchResult(
                    success=False,
                    source_url=video_url,
                    error_code="empty_file",
                    error_message="Downloaded file is empty",
                )
            return FetchResult(
                success=True,
                local_path=local_path,
                source_url=video_url,
                file_size_bytes=size,
            )
        except Exception as exc:
            logger.exception("Failed to fetch %s", video_url)
            return FetchResult(
                success=False,
                source_url=video_url,
                error_code="download_failed",
                error_message=str(exc),
            )

    def _download(self, video_url: str, task_id: str) -> str:
        """Internal download with retry, streaming, and size guard."""

        def _do_download() -> str:
            start = time.monotonic()
            suffix = Path(urlparse(video_url).path).suffix or ".mp4"
            fd, tmp_path = tempfile.mkstemp(
                suffix=suffix, prefix=f"amd_t2_{task_id}_", dir=self.temp_dir
            )
            try:
                with os.fdopen(fd, "wb") as f:
                    with requests.get(
                        video_url, stream=True, timeout=(10, self.timeout)
                    ) as resp:
                        resp.raise_for_status()
                        downloaded = 0
                        for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                            if not chunk:
                                continue
                            downloaded += len(chunk)
                            if downloaded > self.max_size:
                                raise ValueError(
                                    f"File exceeds max size {self.max_size} bytes"
                                )
                            f.write(chunk)
                elapsed = time.monotonic() - start
                logger.info(
                    "Downloaded %s -> %s (%d bytes, %.1fs)",
                    video_url,
                    tmp_path,
                    downloaded,
                    elapsed,
                )
                return tmp_path
            except Exception:
                # Clean up temp file on any failure before retry
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        return self.retry.call(_do_download)