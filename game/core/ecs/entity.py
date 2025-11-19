"""
A simple entity-component system.
"""
from typing import Dict, Type, TypeVar, Any

T = TypeVar('T')


class Entity:
    """A generic game object."""

    def __init__(self, entity_id: int):
        self.entity_id = entity_id
        self._components: Dict[Type, Any] = {}

    def add_component(self, component: Any):
        """Adds a component to the entity."""
        self._components[type(component)] = component

    def get_component(self, component_type: Type[T]) -> T:
        """Gets a component from the entity."""
        return self._components[component_type]

    def has_component(self, component_type: Type) -> bool:
        """Checks if the entity has a component."""
        return component_type in self._components
