from typing import Type, TypeVar, Dict, Any, List, Optional, Tuple
import esper
import uuid

T = TypeVar('T')

class Component:
    """
    Base class for components.

    In Esper, components can be any object, but we keep this class for backward compatibility
    and potential type hinting.
    """
    pass

class World:
    """
    The main ECS (Entity Component System) World class, wrapping esper's context-based API.

    Each instance of this class manages a separate esper World context.
    """

    def __init__(self):
        """Initializes a new ECS World."""
        self.name = str(uuid.uuid4())
        esper.switch_world(self.name)
        self._entities: List[int] = [] # Maintain list for backward compatibility
        # Note: esper doesn't have explicit world creation, switching to a new name creates it.

    def _switch(self):
        """Switches to this world's context."""
        esper.switch_world(self.name)

    def create_entity(self, *components: Any) -> int:
        """
        Creates a new entity.

        Returns:
            int: The unique ID of the newly created entity.
        """
        self._switch()
        entity = esper.create_entity(*components)
        self._entities.append(entity)
        return entity

    def destroy_entity(self, entity: int) -> None:
        """
        Destroys an entity and removes all its components.

        Args:
            entity: The ID of the entity to destroy.
        """
        self._switch()
        if entity in self._entities:
             self._entities.remove(entity)
        try:
            esper.delete_entity(entity, immediate=True)
        except KeyError:
            pass

    def entity_exists(self, entity: int) -> bool:
        """
        Checks if an entity exists.

        Args:
            entity: The ID of the entity.

        Returns:
            bool: True if the entity exists, False otherwise.
        """
        return entity in self._entities

    def add_component(self, entity: int, component: Any) -> None:
        """
        Adds a component to an entity.

        Args:
            entity: The ID of the entity.
            component: The component instance to add.
        """
        self._switch()
        esper.add_component(entity, component)

    def remove_component(self, entity: int, component_type: Type) -> None:
        """
        Removes a component of a specific type from an entity.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to remove.
        """
        self._switch()
        try:
            esper.remove_component(entity, component_type)
        except KeyError:
            pass

    def get_component(self, entity: int, component_type: Type[T]) -> Optional[T]:
        """
        Retrieves a component of a specific type from an entity.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to retrieve.

        Returns:
            Optional[T]: The component instance, or None if the entity does not have it.
        """
        self._switch()
        try:
            return esper.component_for_entity(entity, component_type)
        except KeyError:
            return None

    def has_component(self, entity: int, component_type: Type) -> bool:
        """
        Checks if an entity has a specific component type.

        Args:
            entity: The ID of the entity.
            component_type: The type of component to check for.

        Returns:
            bool: True if the entity has the component, False otherwise.
        """
        self._switch()
        try:
            return esper.has_component(entity, component_type)
        except KeyError:
            return False

    def get_components(self, component_type: Type[T]) -> Dict[int, T]:
        """
        Retrieves all components of a specific type.

        Args:
            component_type: The type of component to retrieve.

        Returns:
            Dict[int, T]: A dictionary mapping entity IDs to component instances.
        """
        self._switch()
        # esper.get_component returns List[Tuple[int, T]]
        return {entity: component for entity, component in esper.get_component(component_type)}

    def get_entities_with(self, *component_types: Type) -> List[int]:
        """
        Retrieves a list of entity IDs that have all specified component types.

        Args:
            *component_types: A variable number of component types.

        Returns:
            List[int]: A list of entity IDs matching the criteria.
        """
        self._switch()
        if not component_types:
            return []
        # esper.get_components returns Iterable[Tuple[int, Tuple[Any, ...]]]
        return [entity for entity, _ in esper.get_components(*component_types)]

    def get_components_tuple(self, *component_types: Type) -> List[Tuple[int, Tuple[Any, ...]]]:
        """
        Retrieves entities and their components for the specified types.

        This maps directly to esper.get_components for efficient iteration.

        Args:
            *component_types: The component types to retrieve.

        Returns:
            List[Tuple[int, Tuple[Any, ...]]]: A list of (entity, (component1, component2, ...)).
        """
        self._switch()
        return esper.get_components(*component_types)

    def add_system(self, system: 'System') -> None:
        """
        Adds a system to the world.

        Args:
            system: The System instance to add.
        """
        self._switch()
        # Inject world reference into system
        # We use 'ecs_world' to avoid conflict with any internal 'world' attribute if esper ever sets one
        system.ecs_world = self
        esper.add_processor(system)

    def update(self, dt: float) -> None:
        """
        Updates all systems in the world.

        Args:
            dt: The time elapsed since the last update in seconds.
        """
        self._switch()
        esper.process(dt)

class System(esper.Processor):
    """
    Base class for systems in the ECS.

    Systems contain logic that operates on entities with specific components.
    """
    ecs_world: World

    def process(self, dt: float) -> None:
        """
        Esper calls this method. We delegate to the update method for backward compatibility.
        """
        # We need to ensure we are operating on the correct world context
        # esper.process is called within the context, so global esper calls are safe.
        # We pass self.ecs_world (our wrapper) to the update method.
        if hasattr(self, 'ecs_world'):
             self.update(self.ecs_world, dt)
        else:
             # This should not happen if added via World.add_system
             pass

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
