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
            # If this is an ECS system, we only initialize it if ecs_world is already set.
            # Otherwise, World.add_system() will call initialize when setting ecs_world.
            is_system = False
            for base in type(instance).__mro__:
                if (
                    base.__name__ == "System"
                    and "yukkuri_game.engine.ecs" in base.__module__
                ):
                    is_system = True
                    break

            if is_system and not hasattr(instance, "ecs_world"):
                # Skip initialization for now, add_system will handle it
                pass
            else:
                try:
                    instance.initialize()
                except Exception:
                    logger.exception(
                        f"Error initializing service {instance}"
                    )

        self._services[key] = instance

    def _is_namespace_compatible(self, t1: Any, t2: Any) -> bool:
        """
        Checks if t1 and t2 are duplicate module namespaces.

        This handles cases where the same module is imported with different
        prefixes (e.g., 'src.yukkuri_game' vs 'yukkuri_game').

        Args:
            t1 (Any): The first type to check.
            t2 (Any): The second type to check.

        Returns:
            bool: True if they are semantically equivalent, False otherwise.
        """
        if t1 == t2:
            return True
        if not isinstance(t1, type) or not isinstance(t2, type):
            return False
        if getattr(t1, "__name__", None) == getattr(t2, "__name__", None):
            m1 = getattr(t1, "__module__", "")
            m2 = getattr(t2, "__module__", "")
            if m1 and m2:
                s1 = m1.split("yukkuri_game.")[-1]
                s2 = m2.split("yukkuri_game.")[-1]
                return s1 == s2
        return False

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

        # Try namespace-compatible lookup first
        for registered_type, instance in self._services.items():
            if self._is_namespace_compatible(registered_type, service_type):
                return cast(T, instance)

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

        available_names = [
            getattr(t, "__name__", str(t)) for t in self._services.keys()
        ]
        logger.error(
            f"Service not found: {service_type}. "
            f"Available: {list(self._services.keys())}"
        )
        raise ServiceNotFoundError(
            f"Service of type {service_type.__name__} not found. "
            f"Registered services: {', '.join(available_names)}"
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

        # Try namespace-compatible lookup first
        for registered_type, instance in self._services.items():
            if self._is_namespace_compatible(registered_type, service_type):
                return cast(T, instance)

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

        # Try namespace-compatible lookup first
        for registered_type in self._services:
            if self._is_namespace_compatible(registered_type, service_type):
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
