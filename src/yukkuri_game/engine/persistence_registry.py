"""
Declarative Component Persistence Registry.

Provides a decorator and a central registry to track ECS component classes
that should be serialized and deserialized.
"""

from typing import (
    Any,
    TypeVar,
)

T = TypeVar("T")


class PersistenceRegistry:
    """
    Central registry tracking persistent component classes.
    """

    _registered_components: set[type[Any]] = set()

    @classmethod
    def register(cls, component_class: type[T]) -> type[T]:
        """
        Registers a component class for serialization.

        Args:
            component_class (type[T]): The component class to register.

        Returns:
            type[T]: The registered component class.
        """
        cls._registered_components.add(component_class)
        return component_class

    @classmethod
    def get_registered_components(cls) -> list[type[Any]]:
        """
        Retrieves all registered persistent component classes.

        Returns:
            list[type[Any]]: A list of registered component classes.
        """
        return list(cls._registered_components)


def persistent(cls: type[T]) -> type[T]:
    """
    Decorator to mark a component class as persistent.

    Example:
        @persistent
        @dataclass
        class MyComponent:
            value: int

    Args:
        cls (type[T]): The class to decorate.

    Returns:
        type[T]: The decorated class.
    """
    return PersistenceRegistry.register(cls)
