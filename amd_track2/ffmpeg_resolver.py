"""Deterministic FFmpeg/ffprobe path resolution with explicit failure modes."""

import logging
import os
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class FFmpegResolutionError(Exception):
    """Raised when FFmpeg cannot be located."""
    pass


class FFprobeResolutionError(Exception):
    """Raised when ffprobe cannot be located."""
    pass


def resolve_ffmpeg(explicit_path: Optional[str] = None) -> str:
    """Resolve ffmpeg path with explicit fallback chain.

    Resolution order:
    1. FFMPEG_PATH environment variable
    2. explicit_path argument
    3. shutil.which("ffmpeg")
    4. Raise FFmpegResolutionError

    Args:
        explicit_path: Optional path provided via configuration

    Returns:
        Resolved ffmpeg executable path

    Raises:
        FFmpegResolutionError: If ffmpeg cannot be found
    """
    # 1. Environment variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and _executable_exists(env_path):
        logger.debug("FFmpeg resolved from FFMPEG_PATH: %s", env_path)
        return env_path

    # 2. Explicit argument
    if explicit_path and _executable_exists(explicit_path):
        logger.debug("FFmpeg resolved from explicit path: %s", explicit_path)
        return explicit_path

    # 3. PATH lookup via shutil.which
    which_path = shutil.which("ffmpeg")
    if which_path:
        logger.debug("FFmpeg resolved from PATH: %s", which_path)
        return which_path

    # 4. Fail explicitly
    raise FFmpegResolutionError(
        "FFmpeg not found. Set FFMPEG_PATH environment variable or provide explicit path."
    )


def resolve_ffprobe(explicit_path: Optional[str] = None) -> str:
    """Resolve ffprobe path with explicit fallback chain.

    Resolution order:
    1. FFPROBE_PATH environment variable
    2. explicit_path argument
    3. shutil.which("ffprobe")
    4. Raise FFprobeResolutionError

    Args:
        explicit_path: Optional path provided via configuration

    Returns:
        Resolved ffprobe executable path

    Raises:
        FFprobeResolutionError: If ffprobe cannot be found
    """
    # 1. Environment variable
    env_path = os.environ.get("FFPROBE_PATH")
    if env_path and _executable_exists(env_path):
        logger.debug("ffprobe resolved from FFPROBE_PATH: %s", env_path)
        return env_path

    # 2. Explicit argument
    if explicit_path and _executable_exists(explicit_path):
        logger.debug("ffprobe resolved from explicit path: %s", explicit_path)
        return explicit_path

    # 3. PATH lookup via shutil.which
    which_path = shutil.which("ffprobe")
    if which_path:
        logger.debug("ffprobe resolved from PATH: %s", which_path)
        return which_path

    # 4. Fail explicitly
    raise FFprobeResolutionError(
        "ffprobe not found. Set FFPROBE_PATH environment variable or provide explicit path."
    )


def _executable_exists(path: str) -> bool:
    """Check if a file exists and is executable."""
    if not path:
        return False
    return os.path.isfile(path) and os.access(path, os.X_OK)