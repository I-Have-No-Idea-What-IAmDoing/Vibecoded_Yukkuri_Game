"""
Module defining the Entity Component System (ECS) wrapper.
"""
from typing import Type, TypeVar, Dict, Any, List, Optional, Tuple, TYPE_CHECKING
import esper
import uuid
from .service_locator import ServiceLocator
from .events import EntityDestroyedEvent
from .event_bus import EventBus

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

    Attributes:
        name (str): The unique name of the world context.
        services (ServiceLocator): The service locator associated with this world.
    """

    def __init__(self) -> None:
        """Initializes a new ECS World."""
        self.name = str(uuid.uuid4())
        esper.switch_world(self.name)
        # Note: esper doesn't have explicit world creation, switching to a new name creates it.
        self.services = ServiceLocator()

    def _switch(self) -> None:
        """Switches to this world's context."""
        if esper.current_world != self.name:
            esper.switch_world(self.name)

    def create_entity(self, *components: Any) -> int:
        """
        Creates a new entity with the given components.

        Args:
            *components (Any): The components to add to the entity.

        Returns:
            int: The unique ID of the newly created entity.
        """
        self._switch()
        # Create entity in the active esper world context
        return int(esper.create_entity(*components))

    def destroy_entity(self, entity: int) -> None:
        """
        Destroys an entity and removes all its components.

        Args:
            entity (int): The ID of the entity to destroy.

        Returns:
            None
        """
        self._switch()
        try:
            # Notify before deletion (or after, but typically useful to know ID is gone)
            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(EntityDestroyedEvent(entity))

            # print(f"DEBUG: destroy_entity {entity} in world {self.name}")
            esper.delete_entity(entity, immediate=True)
            # print(f"DEBUG: exists after delete? {esper.entity_exists(entity)}")
        except KeyError:
            # print(f"DEBUG: destroy_entity {entity} KeyError")
            pass

    def entity_exists(self, entity: int) -> bool:
        """
        Checks if an entity exists.

        Args:
            entity (int): The ID of the entity.

        Returns:
            bool: True if the entity exists, False otherwise.
        """
        self._switch()
        return bool(esper.entity_exists(entity))

    def add_component(self, entity: int, component: Any) -> None:
        """
        Adds a component to an entity.

        Args:
            entity (int): The ID of the entity.
            component (Any): The component instance to add.

        Returns:
            None
        """
        self._switch()
        esper.add_component(entity, component)

    def remove_component(self, entity: int, component_type: Type[Any]) -> None:
        """
        Removes a component of a specific type from an entity.

        Args:
            entity (int): The ID of the entity.
            component_type (Type[Any]): The type of component to remove.

        Returns:
            None
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
            entity (int): The ID of the entity.
            component_type (Type[T]): The type of component to retrieve.

        Returns:
            Optional[T]: The component instance, or None if the entity does not have it.
        """
        self._switch()
        try:
            # Cast because esper might return Any or not be fully typed
            # noinspection PyTypeHints
            return esper.component_for_entity(entity, component_type) # type: ignore[no-any-return]
        except KeyError:
            return None

    def try_get_component(self, entity: int, component_type: Type[T]) -> Optional[T]:
        """Alias for get_component."""
        return self.get_component(entity, component_type)

    def has_component(self, entity: int, component_type: Type[Any]) -> bool:
        """
        Checks if an entity has a specific component type.

        Args:
            entity (int): The ID of the entity.
            component_type (Type[Any]): The type of component to check for.

        Returns:
            bool: True if the entity has the component, False otherwise.
        """
        self._switch()
        try:
            return bool(esper.has_component(entity, component_type))
        except KeyError:
            return False

    def get_components(self, component_type: Type[T]) -> Dict[int, T]:
        """
        Retrieves all components of a specific type.

        Args:
            component_type (Type[T]): The type of component to retrieve.

        Returns:
            Dict[int, T]: A dictionary mapping entity IDs to component instances.
        """
        self._switch()
        # esper.get_component returns List[Tuple[int, T]]
        return {entity: component for entity, component in esper.get_component(component_type)}

    def get_all_entities(self) -> List[int]:
        """
        Retrieves all entity IDs in the current world context.

        Returns:
            List[int]: A list of all entity IDs.
        """
        self._switch()
        # esper._entities is a dictionary {entity_id: {component_type: component_instance}}
        # Since esper doesn't provide a public method to get all entities, we access the internal storage.
        # This is safe because we are wrapping esper and this class is the designated interface.
        # Note: 'esper._entities' is a module-level variable that points to the entity map of the
        # currently active world context (managed by switch_world).
        try:
            # Accessing the internal _entities attribute of esper directly is necessary
            # because the public API focuses on component-based queries.
            # Note: This depends on esper's internal implementation detail `_entities`.
            return list(esper._entities.keys())
        except AttributeError:
            # Fallback if internal implementation changes (unlikely for stable esper)
            # A more robust but slower way would be to query for a common component if we knew one.
            return []

    def get_entities_with(self, *component_types: Type[Any]) -> List[int]:
        """
        Retrieves a list of entity IDs that have all specified component types.

        Args:
            *component_types (Type[Any]): A variable number of component types.

        Returns:
            List[int]: A list of entity IDs matching the criteria.
        """
        self._switch()
        if not component_types:
            return []
        # esper.get_components returns Iterable[Tuple[int, Tuple[Any, ...]]]
        return [entity for entity, _ in esper.get_components(*component_types)]

    def get_components_tuple(self, *component_types: Type[Any]) -> List[Tuple[int, Tuple[Any, ...]]]:
        """
        Retrieves entities and their components for the specified types.

        This maps directly to esper.get_components for efficient iteration.

        Args:
            *component_types (Type[Any]): The component types to retrieve.

        Returns:
            List[Tuple[int, Tuple[Any, ...]]]: A list of (entity, (component1, component2, ...)).
        """
        self._switch()
        # noinspection PyTypeChecker
        return esper.get_components(*component_types) # type: ignore[no-any-return]

    def get_all_components(self, entity: int) -> Tuple[Any, ...]:
        """
        Retrieves all components for a specific entity.

        Args:
            entity (int): The entity ID.

        Returns:
            Tuple[Any, ...]: A tuple of all component instances attached to the entity.
        """
        self._switch()
        try:
            return esper.components_for_entity(entity)
        except KeyError:
            return ()

    def add_system(self, system: 'System') -> None:
        """
        Adds a system to the world.

        Args:
            system (System): The System instance to add.

        Returns:
            None
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
            dt (float): The time elapsed since the last update in seconds.

        Returns:
            None
        """
        self._switch()
        # Process all registered systems (Processors) in order of priority
        # noinspection PyTypeChecker
        esper.process(dt)

    def clear(self) -> None:
        """
        Clears all entities and components from the world.
        Note: This does NOT remove Processors (Systems).
        """
        self._switch()
        esper.clear_database()

if TYPE_CHECKING:
    class ProcessorBase:
        """
        Base class for Processors (Systems).
        Used for type checking against esper.Processor.
        """
        def process(self, dt: float) -> None:
            """
            Processes the system logic.

            Args:
                dt (float): Delta time.
            """
            ...
else:
    ProcessorBase = esper.Processor

class System(ProcessorBase):
    """
    Base class for systems in the ECS.

    Systems contain logic that operates on entities with specific components.

    Attributes:
        ecs_world (World): The ECS World instance the system belongs to.
    """
    ecs_world: World

    def process(self, dt: float) -> None:
        """
        Esper calls this method. We delegate to the update method for backward compatibility.

        Args:
            dt (float): The time elapsed since the last update in seconds.

        Returns:
            None
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
            world (World): The ECS World instance.
            dt (float): The time elapsed since the last update in seconds.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError
