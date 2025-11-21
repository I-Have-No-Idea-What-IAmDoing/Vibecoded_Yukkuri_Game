from typing import Type, TypeVar, Dict, Any, Optional

T = TypeVar('T')

class ServiceNotFoundError(Exception):
    """Raised when a requested service is not found."""
    pass

class ServiceLocator:
    """
    A simple service locator registry.
    Allows registering and retrieving service instances by their class type.
    """

    def __init__(self) -> None:
        self._services: Dict[Type[Any], Any] = {}

    def register(self, instance: Any, service_type: Optional[Type[Any]] = None, replace: bool = False) -> None:
        """
        Registers a service instance.

        Args:
            instance: The service instance to register.
            service_type: The type key to use for registration. If None, the instance's type is used.
            replace: If True, allows overwriting an existing service of the same type.

        Raises:
            ValueError: If the service is already registered and replace is False.
        """
        key = service_type if service_type else type(instance)

        if key in self._services and not replace:
            raise ValueError(f"Service of type {key.__name__} is already registered.")

        self._services[key] = instance

    def get(self, service_type: Type[T]) -> T:
        """
        Retrieves a service instance by its type.

        Args:
            service_type: The type of the service to retrieve.

        Returns:
            The registered service instance.

        Raises:
            ServiceNotFoundError: If the service is not registered.
        """
        service = self._services.get(service_type)
        if service is None:
            raise ServiceNotFoundError(f"Service of type {service_type.__name__} not found.")
        return service # type: ignore

    def try_get(self, service_type: Type[T]) -> Optional[T]:
        """
        Tries to retrieve a service instance by its type.

        Args:
            service_type: The type of the service to retrieve.

        Returns:
            The registered service instance, or None if not found.
        """
        return self._services.get(service_type) # type: ignore
