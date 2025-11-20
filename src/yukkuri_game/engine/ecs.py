from typing import Type, TypeVar, Dict, Any, List, Optional
import uuid

T = TypeVar('T')

class Component:
    """
    Base class for components.

    While not strictly required by this ECS implementation (as any object can be a component),
    inheriting from this class can provide type safety and structure.
    """
    pass

class World:
    """
    The main ECS (Entity Component System) World class.

    Manages entities, components, and systems.

    Attributes:
        _entities (List[int]): A list of active entity IDs.
        _components (Dict[Type, Dict[int, Any]]): A dictionary storing components,
            keyed by component type and then by entity ID.
        _next_entity_id (int): The ID to assign to the next created entity.
        _systems (List[System]): A list of systems registered to the world.
    """

    def __init__(self):
        """Initializes a new ECS World."""
        self._entities: List[int] = []
        self._components: Dict[Type, Dict[int, Any]] = {}
        self._next_entity_id = 0
        self._systems = []

    def create_entity(self) -> int:
        """
        Creates a new entity.

        Returns:
            int: The unique ID of the newly created entity.
        """
        entity = self._next_entity_id
        self._next_entity_id += 1
        self._entities.append(entity)
        return entity

    def destroy_entity(self, entity: int) -> None:
        """
        Destroys an entity and removes all its components.

        Args:
            entity: The ID of the entity to destroy.
        """
        if entity in self._entities:
            self._entities.remove(entity)
            for c_type in self._components:
                if entity in self._components[c_type]:
                    del self._components[c_type][entity]

    def add_component(self, entity: int, component: Any) -> None:
        """
        Adds a component to an entity.

        Args:
            entity: The ID of the entity.
            component: The component instance to add.
        """
        c_type = type(component)
        if c_type not in self._components:
            self._components[c_type] = {}
        self._components[c_type][entity] = component

    def remove_component(self, entity: int, component_type: Type) -> None:
        """
        Removes a component of a specific type from an entity.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to remove.
        """
        if component_type in self._components and entity in self._components[component_type]:
            del self._components[component_type][entity]

    def get_component(self, entity: int, component_type: Type[T]) -> Optional[T]:
        """
        Retrieves a component of a specific type from an entity.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to retrieve.

        Returns:
            Optional[T]: The component instance, or None if the entity does not have it.
        """
        return self._components.get(component_type, {}).get(entity)

    def has_component(self, entity: int, component_type: Type) -> bool:
        """
        Checks if an entity has a specific component type.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to check for.

        Returns:
            bool: True if the entity has the component, False otherwise.
        """
        return entity in self._components.get(component_type, {})

    def get_components(self, component_type: Type[T]) -> Dict[int, T]:
        """
        Retrieves all components of a specific type.

        Args:
            component_type: The type of component to retrieve.

        Returns:
            Dict[int, T]: A dictionary mapping entity IDs to component instances.
        """
        return self._components.get(component_type, {})

    def get_entities_with(self, *component_types: Type) -> List[int]:
        """
        Retrieves a list of entity IDs that have all specified component types.

        Args:
            *component_types: A variable number of component types.

        Returns:
            List[int]: A list of entity IDs matching the criteria.
        """
        if not component_types:
            return []

        # Start with entities having the first component
        first_type = component_types[0]
        entities = set(self._components.get(first_type, {}).keys())

        for c_type in component_types[1:]:
            entities &= set(self._components.get(c_type, {}).keys())

        return list(entities)

    def add_system(self, system: 'System') -> None:
        """
        Adds a system to the world.

        Args:
            system: The System instance to add.
        """
        self._systems.append(system)

    def update(self, dt: float) -> None:
        """
        Updates all systems in the world.

        Args:
            dt: The time elapsed since the last update in seconds.
        """
        for system in self._systems:
            system.update(self, dt)

class System:
    """
    Base class for systems in the ECS.

    Systems contain logic that operates on entities with specific components.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system.

        Args:
            world: The ECS World instance.
            dt: The time elapsed since the last update in seconds.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError
