"""
Custom Exceptions for the Engine.
"""

from typing import Any


class GameEngineError(Exception):
    """Base exception for all game engine errors.

    Supports an optional context dictionary to provide detailed runtime metadata.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Initializes the exception with a message and optional context.

        Args:
            message (str): The exception message.
            context (dict[str, Any] | None): Optional runtime metadata context.
        """
        super().__init__(message)
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        """Returns the formatted exception string, including context if present.

        Returns:
            str: The exception message with context details.
        """
        msg = super().__str__()
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{msg} | Context: {{{context_str}}}"
        return msg


class ResourceLoadError(GameEngineError):
    """Raised when a resource fails to load."""

    pass


class ConfigError(GameEngineError):
    """Raised when configuration data is invalid or missing."""

    pass


class CycleDependencyError(GameEngineError):
    """Raised when a dependency cycle is detected in the system scheduler."""

    pass


class SaveLoadError(GameEngineError):
    """Raised when saving or loading game state fails."""

    pass


class MigrationError(GameEngineError):
    """Raised when JIT persistent data migration fails."""

    pass


class EntityError(GameEngineError):
    """Raised when an ECS entity or component operation encounters an error."""

    pass
