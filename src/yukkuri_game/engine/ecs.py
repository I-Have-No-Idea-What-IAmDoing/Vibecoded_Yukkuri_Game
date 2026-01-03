"""
Module defining the Entity Component System (ECS) wrapper.

This module provides a wrapper around the `esper` library to offer a more
structured and type-safe interface for managing entities and components.
"""

import uuid
from typing import (
    Type,
    TypeVar,
    Dict,
    Any,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Set,
    Iterator,
)
import esper
from .service_locator import ServiceLocator
from .events import (
    EntityDestroyedEvent,
    ComponentAddedEvent,
    ComponentRemovedEvent,
    WorldClearedEvent,
)
from .event_bus import EventBus
import contextlib

T = TypeVar("T")


class Component:
    """
    Base class for components.

    In Esper, components can be any object, but we keep this class for
    explicit typing and potential future extension.
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
        self.services = ServiceLocator()
        self._next_stable_id = 1
        self._active_entities: Set[int] = set()
        # Create the world context in esper
        esper.switch_world(self.name)

    def get_next_stable_id(self) -> int:
        """
        Returns the next unique stable ID for this world.

        The stable ID is used for persistence to identify entities across game sessions,
        separate from the runtime entity ID.

        Returns:
            int: The next available stable ID.
        """
        sid = self._next_stable_id
        self._next_stable_id += 1
        return sid

    def set_next_stable_id(self, next_id: int) -> None:
        """
        Sets the next stable ID manually.

        This is primarily used during level loading to ensure that new entities
        do not conflict with loaded stable IDs.

        Args:
            next_id (int): The next stable ID to use.
        """
        self._next_stable_id = next_id

    def _switch(self) -> None:
        """
        Switches to this world's context.

        Returns:
            None
        """
        # esper uses a global dictionary to store worlds, accessed by name.
        # We ensure the global state points to this world instance.
        if esper.current_world != self.name:
            esper.switch_world(self.name)

    @contextlib.contextmanager
    def context(self) -> Iterator[None]:
        """
        Context manager to ensure operations are performed in this world's context.

        Usage:
            with world.context():
                # perform esper operations directly or via methods

        Yields:
            None
        """
        # Store the previous world to restore it after the block
        previous_world = esper.current_world
        self._switch()
        try:
            yield
        finally:
            # Restore previous context to prevent side effects in other parts of the app
            if previous_world and previous_world != self.name:
                try:
                    esper.switch_world(previous_world)
                except KeyError:
                    # Previous world might have been deleted
                    pass

    def create_entity(self, *components: Any) -> int:
        """
        Creates a new entity with the given components.

        Args:
            *components (Any): The components to add to the entity.

        Returns:
            int: The unique ID of the newly created entity.
        """
        self._switch()
        entity_id = int(esper.create_entity(*components))
        self._active_entities.add(entity_id)

        # Publish ComponentAddedEvent for each component so systems can react
        # (e.g., renderers registering sprites, physics systems creating bodies)
        event_bus = self.services.try_get(EventBus)
        if event_bus:
            for component in components:
                event_bus.publish(
                    ComponentAddedEvent(entity_id, type(component), component)
                )

        return entity_id

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
            # Notify before deletion
            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(EntityDestroyedEvent(entity))

            esper.delete_entity(entity, immediate=True)
            self._active_entities.discard(entity)
        except KeyError:
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

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(ComponentAddedEvent(entity, type(component), component))

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
            # esper.remove_component returns the removed component instance
            removed_component = esper.remove_component(entity, component_type)

            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(
                    ComponentRemovedEvent(entity, component_type, removed_component)
                )
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
            return esper.component_for_entity(entity, component_type)  # type: ignore[no-any-return]
        except KeyError:
            return None

    def try_get_component(self, entity: int, component_type: Type[T]) -> Optional[T]:
        """
        Alias for get_component.

        Args:
            entity (int): The ID of the entity.
            component_type (Type[T]): The type of component to retrieve.

        Returns:
            Optional[T]: The component instance, or None if the entity does not have it.
        """
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
        return {
            entity: component
            for entity, component in esper.get_component(component_type)
        }

    def get_all_entities(self) -> List[int]:
        """
        Retrieves all entity IDs in the current world context.

        Returns:
            List[int]: A list of all entity IDs.
        """
        # We maintain a separate set of entities to avoid accessing private members of esper
        return list(self._active_entities)

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
        return [entity for entity, _ in esper.get_components(*component_types)]

    def get_components_tuple(
        self, *component_types: Type[Any]
    ) -> List[Tuple[int, Tuple[Any, ...]]]:
        """
        Retrieves entities and their components for the specified types.

        This maps directly to esper.get_components for efficient iteration.

        Args:
            *component_types (Type[Any]): The component types to retrieve.

        Returns:
            List[Tuple[int, Tuple[Any, ...]]]: A list of (entity, (component1, component2, ...)).
        """
        self._switch()
        return esper.get_components(*component_types)  # type: ignore[no-any-return]

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

    def add_system(self, system: "System") -> None:
        """
        Adds a system to the world.

        Args:
            system (System): The System instance to add.

        Returns:
            None
        """
        self._switch()
        # Inject world reference into system
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
        esper.process(dt)

    def clear_database(self) -> None:
        """
        Clears all entities and components from the world.
        Note: This does NOT remove Processors (Systems).

        Returns:
            None
        """
        self._switch()
        esper.clear_database()
        self._active_entities.clear()

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(WorldClearedEvent())


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

            Returns:
                None
            """
            ...
else:
    ProcessorBase = esper.Processor


class System(ProcessorBase):
    """
    Base class for systems in the ECS.

    Systems contain logic that operates on entities with specific components.
    Subclasses should implement the `update` method.

    Attributes:
        ecs_world (World): The ECS World instance the system belongs to.
                           Injected when the system is added to the World.
    """

    ecs_world: World

    def process(self, dt: float) -> None:
        """
        The method called by the ECS engine (Esper) every frame.

        This implementation ensures the correct world context is active before
        delegating to the user-defined `update` method.

        Args:
            dt (float): The time elapsed since the last update in seconds.
        """
        # We need to ensure we are operating on the correct world context
        if hasattr(self, "ecs_world"):
            with self.ecs_world.context():
                self.update(self.ecs_world, dt)
        else:
            # Fallback if ecs_world wasn't injected (shouldn't happen if used correctly)
            # Pass a dummy or try to proceed if update doesn't use world (rare)
            pass

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system logic. Must be implemented by subclasses.

        Args:
            world (World): The ECS World instance.
            dt (float): The time elapsed since the last update in seconds.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError
