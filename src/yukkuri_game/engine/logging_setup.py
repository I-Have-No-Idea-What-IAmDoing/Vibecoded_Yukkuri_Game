"""
Logging Setup Module.

Configures Loguru sinks for the game application. Should be called once
at startup before any other imports use the logger.
"""

import sys
from pathlib import Path

from loguru import logger

# Default log directory relative to the working directory.
DEFAULT_LOG_DIR = Path("logs")


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    log_to_file: bool = True,
) -> Path | None:
    """
    Configures Loguru with a console sink and an optional file sink.

    Removes the default Loguru handler and replaces it with:
    - A stderr sink at the requested level (colorized).
    - A rotating file sink at DEBUG level (if log_to_file is True).

    Args:
        level: Minimum log level for the console sink (e.g. "INFO",
            "DEBUG", "WARNING"). Case-insensitive.
        log_file: Explicit path for the log file. If None and
            log_to_file is True, a timestamped file is created under
            ``logs/``.
        log_to_file: Whether to write logs to a file at all.

    Returns:
        The resolved Path of the log file, or None if file logging is
        disabled.
    """
    # Remove the default Loguru handler (stderr, WARNING level).
    logger.remove()

    # --- Console sink ---
    logger.add(
        sys.stderr,
        level=level.upper(),
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        enqueue=False,
    )

    resolved_log_file: Path | None = None

    if log_to_file:
        if log_file is None:
            from datetime import datetime

            DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = DEFAULT_LOG_DIR / f"game_{timestamp}.log"

        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_file),
            level="DEBUG",
            rotation="10 MB",
            retention=5,
            encoding="utf-8",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{line} — {message}"
            ),
            enqueue=False,
            backtrace=True,
            diagnose=True,
        )

        resolved_log_file = log_file
        logger.info(f"Log file: {log_file.resolve()}")

    logger.info(
        f"Logging initialised — console level={level.upper()}, "
        f"file={'disabled' if not log_to_file else str(resolved_log_file)}"
    )

    return resolved_log_file
