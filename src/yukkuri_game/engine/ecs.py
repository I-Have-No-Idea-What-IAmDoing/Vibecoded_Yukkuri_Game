"""
Entity Component System (ECS) Module.

This module provides a wrapper around the `esper` library to offer a more
structured and type-safe interface for managing entities and components.
It integrates with the `ServiceLocator` and `EventBus` for system-wide communication.
"""

import contextlib
import uuid
from collections.abc import Iterator, Callable
from functools import wraps
from typing import Any, TypeVar

import esper

from .event_bus import EventBus
from .events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    EntityDestroyedEvent,
)
from .service_locator import ServiceLocator

T = TypeVar("T")


class Component:
    """Base class for all components."""
    pass




def ensure_context(func: Callable) -> Callable:
    """Decorator to ensure operations run within this world's context."""
    @wraps(func)
    def wrapper(self: "World", *args: Any, **kwargs: Any) -> Any:
        self._switch()
        return func(self, *args, **kwargs)
    return wrapper

class World:
    """
    The main ECS World manager, wrapping an `esper.World` instance.

    Each `World` instance manages its own isolated game state, allowing for
    multiple independent worlds (e.g., active gameplay vs. pause menus).

    Attributes:
        services (ServiceLocator): Service registry specific to this world.
    """

    def __init__(self) -> None:
        """Initializes a new ECS World with a unique service locator."""
        self.name: str = str(uuid.uuid4())
        self.services: ServiceLocator = ServiceLocator()
        self._next_stable_id: int = 1
        self._active_entities: set[int] = set()

        # Register this world with esper's global context system.
        esper.switch_world(self.name)

    def _switch(self) -> None:
        """
        Switches the global esper context to this world's state.

        Optimized to avoid redundant context switches if this world is already active.
        """
        if esper.current_world != self.name:
            esper.switch_world(self.name)

    @contextlib.contextmanager
    def context(self) -> Iterator["World"]:
        """
        Context manager for safely performing operations in this world.

        Ensures the esper global state is correctly switched to this world.
        """
        self._switch()
        yield self

    @property
    def time(self) -> float:
        """
        Retrieves the current elapsed game time.

        Returns:
            float: Elapsed time in seconds. Returns 0.0 if the TimeService is unavailable.
        """
        # Lazy import to avoid circular dependency
        from ..game.services import TimeService

        time_service = self.services.try_get(TimeService)
        return time_service.time_elapsed if time_service else 0.0

    def get_next_stable_id(self) -> int:
        """
        Generates the next unique stable ID.

        Stable IDs are used for persistence, identifying entities across game sessions
        independently of their runtime entity ID.

        Returns:
            int: The next available stable ID.
        """
        sid = self._next_stable_id
        self._next_stable_id += 1
        return sid

    def set_next_stable_id(self, next_id: int) -> None:
        """
        Manually sets the next stable ID counter.

        Used during level loading to prevent conflicts with loaded entity IDs.

        Args:
            next_id (int): The next stable ID to be used.
        """
        self._next_stable_id = next_id

    @ensure_context
    def create_entity(self, *components: Any) -> int:
        """
        Creates a new entity composed of the provided components.

        Publishes a `ComponentAddedEvent` for each attached component.

        Args:
            *components (Any): Variable list of component instances to attach.

        Returns:
            int: The unique runtime ID of the created entity.
        """
        entity_id = int(esper.create_entity(*components))
        self._active_entities.add(entity_id)

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            for component in components:
                event_bus.publish(
                    ComponentAddedEvent(entity_id, type(component), component)
                )

        return entity_id

    @ensure_context
    def destroy_entity(self, entity: int) -> None:
        """
        Removes an entity and all its components from the world.

        Publishes an `EntityDestroyedEvent` before deletion. Safe to call even if
        the entity does not exist (no-op).

        Args:
            entity (int): The ID of the entity to destroy.
        """
        try:
            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(EntityDestroyedEvent(entity))

            esper.delete_entity(entity, immediate=True)
            self._active_entities.discard(entity)
        except KeyError:
            pass

    @ensure_context
    def entity_exists(self, entity: int) -> bool:
        """
        Checks if an entity ID represents a valid, active entity.

        Args:
            entity (int): The ID to check.

        Returns:
            bool: True if the entity exists in this world, False otherwise.
        """
        return bool(esper.entity_exists(entity))

    @ensure_context
    def add_component(self, entity: int, component: Any) -> None:
        """
        Attaches a single component to an existing entity.

        Publishes a `ComponentAddedEvent`.

        Args:
            entity (int): The target entity ID.
            component (Any): The component instance to add.
        """
        esper.add_component(entity, component)

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(ComponentAddedEvent(entity, type(component), component))

    @ensure_context
    def remove_component(self, entity: int, component_type: type[Any]) -> None:
        """
        Detaches a component of the specified type from an entity.

        Publishes a `ComponentRemovedEvent`. Safe to call if the component is missing.

        Args:
            entity (int): The target entity ID.
            component_type (type[Any]): The class of the component to remove.
        """
        try:
            removed_component = esper.remove_component(entity, component_type)

            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(
                    ComponentRemovedEvent(entity, component_type, removed_component)
                )
        except KeyError:
            pass

    @ensure_context
    def get_component(self, entity: int, component_type: type[T]) -> T:
        """
        Retrieves a specific component from an entity. Raises KeyError if missing.

        Args:
            entity (int): The entity ID.
            component_type (type[T]): The class of the component to retrieve.

        Returns:
            T: The component instance.
        """
        return esper.component_for_entity(entity, component_type)

    @ensure_context
    def try_get_component(self, entity: int, component_type: type[T]) -> T | None:
        """
        Safely retrieves a component without raising exceptions if missing.

        Optimized to avoid try-except overhead using `esper.try_component`.

        Args:
            entity (int): The entity ID.
            component_type (type[T]): The class of the component to retrieve.

        Returns:
            T | None: The component instance if found, otherwise None.
        """
        return esper.try_component(entity, component_type)

    @ensure_context
    def has_component(self, entity: int, component_type: type[Any]) -> bool:
        """
        Checks if an entity matches a specific component type.

        Args:
            entity (int): The entity ID.
            component_type (type[Any]): The component class to check for.

        Returns:
            bool: True if the entity satisfies the component requirement, False otherwise.
        """
        try:
            return bool(esper.has_component(entity, component_type))
        except KeyError:
            return False

    @ensure_context
    def get_components(self, component_type: type[T]) -> dict[int, T]:
        """
        Retrieves all instances of a specific component type across all entities.

        Args:
            component_type (type[T]): The component class to query.

        Returns:
            dict[int, T]: A dictionary mapping Entity ID -> Component Instance.
        """
        return {
            entity: component
            for entity, component in esper.get_component(component_type)
        }

    def get_all_entities(self) -> list[int]:
        """
        Retrieves all active entity IDs in this world.

        Returns:
            list[int]: A list of all entity IDs.
        """
        return list(self._active_entities)

    @ensure_context
    def get_entities_with(self, *component_types: type[Any]) -> list[int]:
        """
        Finds entities that possess ALL of the specified component types.

        Args:
            *component_types (type[Any]): Variable list of component classes to direct the query.

        Returns:
            list[int]: A list of matching entity IDs.
        """
        if not component_types:
            return []
        return [entity for entity, _ in esper.get_components(*component_types)]

    def get_components_tuple(
        self, *component_types: type[Any]
    ) -> list[tuple[int, tuple[Any, ...]]]:
        """
        Efficiently retrieves entities and their components for a specific query signature.

        This method maps directly to `esper.get_components` and is preferred for
        iterating over entities in Systems.

        Args:
            *component_types (type[Any]): The component classes to query.

        Returns:
            list[tuple[int, tuple[Any, ...]]]: A list of tuples, where each tuple contains:
                (Entity ID, (Component1, Component2, ...))
        """
        self._switch()
        return esper.get_components(*component_types)

    @ensure_context
    def get_all_components(self, entity: int) -> tuple[Any, ...]:
        """
        Retrieves every component attached to a specific entity.

        Args:
            entity (int): The entity ID.

        Returns:
            tuple[Any, ...]: A tuple containing all component instances for the entity.
        """
        try:
            return esper.components_for_entity(entity)
        except KeyError:
            return ()

    @ensure_context
    def add_system(self, system: "System") -> None:
        """
        Registers a System to run in this world.

        Injection:
            Sets `system.ecs_world` to this World instance.

        Args:
            system (System): The System instance to register.
        """
        system.ecs_world = self
        system.initialize()
        esper.add_processor(system)

    @ensure_context
    def update(self, dt: float) -> None:
        """
        Advances the world state by one tick.

        Executes all registered Systems in priority order.

        Args:
            dt (float): Delta time in seconds since the last frame.
        """
        esper.process(dt)

    @ensure_context
    def clear_database(self) -> None:
        """
        Removes all entities and components. Does NOT remove registered Systems.
        """
        esper.clear_database()
        self._active_entities.clear()

    @ensure_context
    def destroy(self) -> None:
        """
        Completely tears down the world.

        Clears the database, clears services, and removes all systems.
        This is essential for memory management when unloading levels or closing the game.
        """
        self.clear_database()
        self.services.clear()
        # Remove all systems to prevent leaks
        # esper 3.x uses list(_processors)
        for system_instance in list(esper._processors):
            esper.remove_processor(type(system_instance))
        
        # Finally delete the world context
        try:
            esper.delete_world(self.name)
        except PermissionError:
            # Current world cannot be deleted, this is fine if we are tearing down
            pass


class System(esper.Processor):
    """
    Base class for all ECS Systems.

    Systems hold game logic and operate on entities that possess specific components.
    Subclasses must implement the `update` method.

    Attributes:
        ecs_world (World): reference to the World this system belongs to. Injected automatically.
    """

    ecs_world: World

    def process(self, dt: float) -> None:
        """
        Internal wrapper called by Esper every frame.

        Args:
            dt (float): Delta time in seconds.
        """
        if hasattr(self, "ecs_world"):
            self.update(self.ecs_world, dt)

    def initialize(self) -> None:
        """
        Lifecycle hook called when the system is first added to the World.

        Override this to perform setup tasks like subscribing to events.
        """

    def update(self, world: World, dt: float) -> None:
        """
        The core logic loop for the system.

        Must be implemented by subclasses.

        Args:
            world (World): The active ECS World instance.
            dt (float): Delta time in seconds.

        Raises:
            NotImplementedError: If not overridden by the subclass.
        """
        raise NotImplementedError
