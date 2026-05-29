"""
Tests for the logging_setup module.

Verifies that setup_logging correctly configures Loguru sinks,
that the file sink captures DEBUG records, and that CLI/config
overrides work as expected.
"""

import sys
from pathlib import Path

import pytest
from loguru import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_loguru() -> None:
    """Remove all Loguru sinks to ensure a clean state between tests."""
    logger.remove()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_file_sink_created(self, tmp_path: Path) -> None:
        """setup_logging should create the log file at the given path."""
        from yukkuri_game.engine.logging_setup import setup_logging

        _reset_loguru()
        log_file = tmp_path / "test.log"
        result = setup_logging(level="DEBUG", log_file=log_file, log_to_file=True)

        assert result == log_file
        # Write a record and flush
        logger.debug("hello from test")
        # The file should now exist
        assert log_file.exists()

    def test_file_sink_captures_debug(self, tmp_path: Path) -> None:
        """DEBUG-level records should appear in the file sink."""
        from yukkuri_game.engine.logging_setup import setup_logging

        _reset_loguru()
        log_file = tmp_path / "debug.log"
        setup_logging(level="DEBUG", log_file=log_file, log_to_file=True)

        logger.debug("debug_marker_xyz")
        content = log_file.read_text(encoding="utf-8")
        assert "debug_marker_xyz" in content

    def test_file_disabled_returns_none(self, tmp_path: Path) -> None:
        """When log_to_file=False, no file should be written and None returned."""
        from yukkuri_game.engine.logging_setup import setup_logging

        _reset_loguru()
        result = setup_logging(level="INFO", log_to_file=False)

        assert result is None

    def test_default_log_dir_created(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no log_file is given, setup_logging creates logs/ automatically."""
        from yukkuri_game.engine import logging_setup

        # Redirect DEFAULT_LOG_DIR so we don't pollute the repo root.
        monkeypatch.setattr(logging_setup, "DEFAULT_LOG_DIR", tmp_path / "logs")
        _reset_loguru()

        result = logging_setup.setup_logging(level="INFO", log_to_file=True)

        assert result is not None
        assert result.parent == tmp_path / "logs"
        assert result.exists()

    def test_info_level_suppresses_debug_on_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Console sink at INFO should not print DEBUG records to stderr."""
        from yukkuri_game.engine.logging_setup import setup_logging

        _reset_loguru()
        log_file = tmp_path / "console.log"
        setup_logging(level="INFO", log_file=log_file, log_to_file=True)

        logger.debug("should_not_appear_on_console")
        captured = capsys.readouterr()
        assert "should_not_appear_on_console" not in captured.err

    def test_rotation_config_doesnt_crash(self, tmp_path: Path) -> None:
        """Ensure that the rotation/retention kwargs don't raise at add() time."""
        from yukkuri_game.engine.logging_setup import setup_logging

        _reset_loguru()
        log_file = tmp_path / "rotate.log"
        # Should not raise
        setup_logging(level="DEBUG", log_file=log_file, log_to_file=True)


class TestDebugConfig:
    """Tests for the DebugConfig integration in config.py."""

    def test_debug_config_defaults(self) -> None:
        """DebugConfig should default to INFO level and log_to_file=True."""
        from yukkuri_game.config import DebugConfig

        cfg = DebugConfig()
        assert cfg.log_level == "INFO"
        assert cfg.log_to_file is True
        assert cfg.debug_overlay_on_start is False

    def test_load_config_includes_debug(self, tmp_path: Path) -> None:
        """load_config should parse [debug] from config.toml."""
        from yukkuri_game.config import load_config

        config_toml = tmp_path / "config.toml"
        config_toml.write_text(
            '[debug]\nlog_level = "DEBUG"\nlog_to_file = false\n',
            encoding="utf-8",
        )
        # Create a minimal rules.toml so load_config doesn't error
        (tmp_path / "rules.toml").write_text("", encoding="utf-8")

        cfg = load_config(data_dir=tmp_path)
        assert cfg.debug.log_level == "DEBUG"
        assert cfg.debug.log_to_file is False

    def test_load_config_debug_defaults_when_missing(
        self, tmp_path: Path
    ) -> None:
        """load_config should use DebugConfig defaults when [debug] is absent."""
        from yukkuri_game.config import load_config

        # config.toml without [debug] section
        (tmp_path / "config.toml").write_text(
            "[world]\nwidth = 1000\nheight = 1000\n", encoding="utf-8"
        )
        (tmp_path / "rules.toml").write_text("", encoding="utf-8")

        cfg = load_config(data_dir=tmp_path)
        assert cfg.debug.log_level == "INFO"
        assert cfg.debug.log_to_file is True
