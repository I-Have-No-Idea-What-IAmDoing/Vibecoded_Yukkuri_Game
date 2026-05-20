from typing import cast, Any
"""
Tests for the ServiceLocator.
"""

import pytest

from yukkuri_game.engine.service_locator import ServiceLocator, ServiceNotFoundError


class DummyService:
    """Simple service object for testing."""

    def __init__(self) -> None:
        self.shutdown_called = False
        self.cleanup_called = False

    def shutdown(self) -> None:
        """Marks shutdown as called."""
        self.shutdown_called = True

    def cleanup(self) -> None:
        """Marks cleanup as called."""
        self.cleanup_called = True


class CleanupOnlyService:
    """Service with cleanup only."""

    def __init__(self) -> None:
        self.cleanup_called = False

    def cleanup(self) -> None:
        """Marks cleanup as called."""
        self.cleanup_called = True


def test_register_and_get_default_type() -> None:
    """Registers a service by its instance type and retrieves it."""
    locator = ServiceLocator()
    service = DummyService()

    locator.register(service)

    assert locator.get(DummyService) is service
    assert locator.try_get(DummyService) is service
    assert locator.is_registered(DummyService)


def test_register_with_explicit_type() -> None:
    """Registers a service under a custom type and retrieves it."""
    class CustomKey:
        """Custom type key for registration."""
        pass

    locator = ServiceLocator()
    service = DummyService()

    locator.register(service, service_type=CustomKey)

    assert cast(Any, locator.get(CustomKey)) is service
    assert cast(Any, locator.try_get(CustomKey)) is service
    assert locator.is_registered(CustomKey)


def test_register_duplicate_without_replace_raises() -> None:
    """Registering the same type twice without replace raises ValueError."""
    locator = ServiceLocator()
    locator.register(DummyService())

    with pytest.raises(ValueError):
        locator.register(DummyService())


def test_register_duplicate_with_replace_overwrites() -> None:
    """Registering with replace=True overwrites existing service."""
    locator = ServiceLocator()
    original = DummyService()
    replacement = DummyService()

    locator.register(original)
    locator.register(replacement, replace=True)

    assert locator.get(DummyService) is replacement


def test_get_missing_service_raises() -> None:
    """Missing services raise ServiceNotFoundError on get()."""
    locator = ServiceLocator()

    with pytest.raises(ServiceNotFoundError):
        locator.get(DummyService)


def test_try_get_missing_service_returns_none() -> None:
    """Missing services return None on try_get()."""
    locator = ServiceLocator()

    assert locator.try_get(DummyService) is None
    assert not locator.is_registered(DummyService)


def test_clear_calls_shutdown_and_cleanup() -> None:
    """clear() calls shutdown or cleanup on services when present."""
    locator = ServiceLocator()
    shutdown_service = DummyService()
    cleanup_service = CleanupOnlyService()

    locator.register(shutdown_service)
    locator.register(cleanup_service)

    locator.clear()

    assert shutdown_service.shutdown_called
    assert cleanup_service.cleanup_called
    assert not locator.is_registered(DummyService)
    assert not locator.is_registered(CleanupOnlyService)


def test_service_locator_protocol_fallback() -> None:
    """Verifies fallback lookup for runtime-checkable protocols."""
    from typing import Protocol, runtime_checkable

    @runtime_checkable
    class IMockService(Protocol):
        def greet(self) -> str:
            ...

    class MockServiceImpl:
        def greet(self) -> str:
            return "hello"

    locator = ServiceLocator()
    service = MockServiceImpl()

    # Case 1: Register under concrete class, retrieve under protocol
    locator.register(service, service_type=MockServiceImpl)
    assert locator.get(IMockService) is service
    assert locator.try_get(IMockService) is service
    assert locator.is_registered(IMockService)

    # Case 2: Register under protocol, retrieve under concrete class
    locator.clear()
    locator.register(service, service_type=IMockService)
    assert locator.get(MockServiceImpl) is service
    assert locator.try_get(MockServiceImpl) is service
    assert locator.is_registered(MockServiceImpl)
