"""
Module defining the ServiceLocator pattern.
"""

from typing import TypeVar, Any

T = TypeVar("T")


class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found."""

    pass


class ServiceLocator:
    """
    A simple service locator registry.
    Allows registering and retrieving service instances by their class type.

    Attributes:
        _services (Dict[Type[Any], Any]): A dictionary mapping service types to service instances.
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
            service_type (Optional[Type[Any]]): The type key to use for registration. If None, the instance's type is used.
            replace (bool): If True, allows overwriting an existing service of the same type. Defaults to False.

        Returns:
            None

        Raises:
            ValueError: If the service is already registered and replace is False.
        """
        key = service_type if service_type else type(instance)

        if key in self._services and not replace:
            raise ValueError(f"Service of type {key.__name__} is already registered.")

        self._services[key] = instance

    def get(self, service_type: type[T]) -> T:
        """
        Retrieves a service instance by its type.

        Args:
            service_type (Type[T]): The type of the service to retrieve.

        Returns:
            T: The registered service instance.

        Raises:
            ServiceNotFoundError: If the service is not registered.
        """
        service = self._services.get(service_type)
        if service is None:
            raise ServiceNotFoundError(
                f"Service of type {service_type.__name__} not found."
            )
        return service

    def try_get(self, service_type: type[T]) -> T | None:
        """
        Tries to retrieve a service instance by its type.

        Args:
            service_type (Type[T]): The type of the service to retrieve.

        Returns:
            Optional[T]: The registered service instance, or None if not found.
        """
        return self._services.get(service_type)

    def clear(self) -> None:
        """
        Clears all registered services.
        Useful for testing or resetting state.

        Returns:
            None
        """
        self._services.clear()
