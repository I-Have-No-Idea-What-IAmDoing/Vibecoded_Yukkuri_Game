"""
Custom Exceptions for the Engine.
"""


class GameEngineError(Exception):
    """Base exception for all game engine errors."""

    pass


class ResourceLoadError(GameEngineError):
    """Raised when a resource fails to load."""

    pass


class ConfigError(GameEngineError):
    """Raised when configuration data is invalid or missing."""

    pass
