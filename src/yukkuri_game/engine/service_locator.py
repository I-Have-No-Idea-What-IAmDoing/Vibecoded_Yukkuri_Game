"""
Module defining the ServiceLocator pattern.
"""

from typing import Any, TypeVar, cast
from loguru import logger


T = TypeVar("T")


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found."""

    pass


class ServiceLocator:
    """
    A simple service locator registry.
    Allows registering and retrieving service instances by their class type.

    Attributes:
        _services (dict[type[Any], Any]): A dictionary mapping service types to service instances.
    """

    def __init__(self) -> None:
        """Initializes the ServiceLocator."""
        self._services: dict[type[Any], Any] = {}

    def register(
        self,
        instance: Any,
        service_type: type[Any] | None = None,
        replace: bool = False,
    ) -> None:
        """
        Registers a service instance.

        Args:
            instance (Any): The service instance to register.
            service_type (type[Any] | None): The type key to use for registration. If None, the instance's type is used.
            replace (bool): If True, allows overwriting an existing service of the same type. Defaults to False.

        Raises:
            ValueError: If the service is already registered and replace is False.
        """
        key = service_type if service_type else type(instance)

        if key in self._services:
            if not replace:
                type_name = getattr(key, "__name__", str(key))
                raise ValueError(
                    f"Service of type {type_name} is already registered."
                )
            # Shutdown old service if replace is True
            old_service = self._services[key]
            if (
                hasattr(old_service, "shutdown")
                and callable(old_service.shutdown)
            ):
                try:
                    old_service.shutdown()
                except Exception:
                    logger.exception(
                        f"Error shutting down service {old_service}"
                    )
            elif (
                hasattr(old_service, "cleanup")
                and callable(old_service.cleanup)
            ):
                try:
                    old_service.cleanup()
                except Exception:
                    logger.exception(
                        f"Error cleaning up service {old_service}"
                    )

        # Call initialize if available
        if hasattr(instance, "initialize") and callable(instance.initialize):
            try:
                instance.initialize()
            except Exception:
                logger.exception(
                    f"Error initializing service {instance}"
                )

        self._services[key] = instance

    def get(self, service_type: type[T]) -> T:
        """
        Retrieves a service instance by its type.

        Args:
            service_type (type[T]): The type of the service to retrieve.

        Returns:
            T: The registered service instance.

        Raises:
            ServiceNotFoundError: If the service is not registered.
        """
        if service_type in self._services:
            return cast(T, self._services[service_type])

        # Fallback check for protocol/subclass compatibility
        for registered_type, instance in self._services.items():
            try:
                if (
                    isinstance(registered_type, type)
                    and issubclass(registered_type, service_type)
                ):
                    return cast(T, instance)
            except TypeError:
                pass
            try:
                if isinstance(instance, service_type):
                    return cast(T, instance)
            except TypeError:
                pass

        logger.error(
            f"Service not found: {service_type}. "
            f"Available: {list(self._services.keys())}"
        )
        raise ServiceNotFoundError(
            f"Service of type {service_type.__name__} not found."
        )

    def try_get(self, service_type: type[T]) -> T | None:
        """
        Tries to retrieve a service instance by its type.

        Args:
            service_type (type[T]): The type of the service to retrieve.

        Returns:
            T | None: The registered service instance, or None if not found.
        """
        if service_type in self._services:
            return cast(T, self._services[service_type])

        # Fallback check for protocol/subclass compatibility
        for registered_type, instance in self._services.items():
            try:
                if (
                    isinstance(registered_type, type)
                    and issubclass(registered_type, service_type)
                ):
                    return cast(T, instance)
            except TypeError:
                pass
            try:
                if isinstance(instance, service_type):
                    return cast(T, instance)
            except TypeError:
                pass

        return None

    def is_registered(self, service_type: type[Any]) -> bool:
        """
        Checks whether a service type is registered.

        Args:
            service_type (type[Any]): The type of the service to check.

        Returns:
            bool: True if the service is registered, False otherwise.
        """
        if service_type in self._services:
            return True

        # Fallback check for protocol/subclass compatibility
        for registered_type, instance in self._services.items():
            try:
                if (
                    isinstance(registered_type, type)
                    and issubclass(registered_type, service_type)
                ):
                    return True
            except TypeError:
                pass
            try:
                if isinstance(instance, service_type):
                    return True
            except TypeError:
                pass

        return False

    def unregister(self, service_type: type[Any]) -> None:
        """
        Unregisters a service type.

        Args:
            service_type (type[Any]): The type of the service to unregister.
        """
        if service_type in self._services:
            service = self._services[service_type]
            if hasattr(service, "shutdown") and callable(service.shutdown):
                try:
                    service.shutdown()
                except Exception:
                    logger.exception(
                        f"Error shutting down service {service}"
                    )
            elif hasattr(service, "cleanup") and callable(service.cleanup):
                try:
                    service.cleanup()
                except Exception:
                    logger.exception(
                        f"Error cleaning up service {service}"
                    )
            del self._services[service_type]

    def clear(self) -> None:
        """
        Clears all registered services.
        Calls shutdown() on services if they have it.
        Useful for testing or resetting state.
        """
        for service in self._services.values():
            if hasattr(service, "shutdown") and callable(service.shutdown):
                try:
                    service.shutdown()
                except Exception:
                    logger.exception(
                        f"Error shutting down service {service}"
                    )
            elif hasattr(service, "cleanup") and callable(service.cleanup):
                try:
                    service.cleanup()
                except Exception:
                    logger.exception(
                        f"Error cleaning up service {service}"
                    )

        self._services.clear()
