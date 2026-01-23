"""
Entity Component System (ECS) Module.

This module provides a wrapper around the `esper` library to offer a more
structured and type-safe interface for managing entities and components.
It integrates with the `ServiceLocator` and `EventBus` for system-wide communication.
"""

import contextlib
import uuid
from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

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
    """
    Base class for all components.

    While `esper` allows any object to be a component, inheriting from this class
    ensures explicit typing and provides a hook for potential future extensions.
    """

    pass


class World:
    """
    The main ECS World manager, wrapping `esper`'s context-based API.

    Each `World` instance manages a distinct `esper` context, allowing for multiple
    isolated game states (e.g., active gameplay vs. pause menus).

    Attributes:
        name (str): Unique identifier for this world context.
        services (ServiceLocator): Service registry specific to this world.
    """

    def __init__(self) -> None:
        """Initializes a new ECS World with a unique ID and service locator."""
        self.name = str(uuid.uuid4())
        self.services = ServiceLocator()
        self._next_stable_id = 1
        self._active_entities: set[int] = set()

        # Register this world with esper's global context system.
        esper.switch_world(self.name)

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
            next_id: The next stable ID to be used.
        """
        self._next_stable_id = next_id

    def _switch(self) -> None:
        """
        Activates this world's context in `esper`.

        Optimized to avoid redundant context switches if this world is already active.
        """
        if esper.current_world is not self.name and esper.current_world != self.name:
            esper.switch_world(self.name)

    @contextlib.contextmanager
    def context(self) -> Iterator[None]:
        """
        Context manager for executing operations within this world's scope.

        Ensures that `esper` operations performed inside the `with` block apply
        to this world instances, restoring the previous context afterwards.

        Yields:
            None
        """
        previous_world = esper.current_world
        self._switch()
        try:
            yield
        finally:
            if previous_world and previous_world != self.name:
                try:
                    esper.switch_world(previous_world)
                except KeyError:
                    pass  # Previous world was deleted during execution.

    def create_entity(self, *components: Any) -> int:
        """
        Creates a new entity composed of the provided components.

        Publishes a `ComponentAddedEvent` for each attached component.

        Args:
            *components: Variable list of component instances to attach.

        Returns:
            int: The unique runtime ID of the created entity.
        """
        self._switch()
        entity_id = int(esper.create_entity(*components))
        self._active_entities.add(entity_id)

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            for component in components:
                event_bus.publish(
                    ComponentAddedEvent(entity_id, type(component), component)
                )

        return entity_id

    def destroy_entity(self, entity: int) -> None:
        """
        Removes an entity and all its components from the world.

        Publishes an `EntityDestroyedEvent` before deletion. Safe to call even if
        the entity does not exist (no-op).

        Args:
            entity: The ID of the entity to destroy.
        """
        self._switch()
        try:
            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(EntityDestroyedEvent(entity))

            esper.delete_entity(entity, immediate=True)
            self._active_entities.discard(entity)
        except KeyError:
            pass

    def entity_exists(self, entity: int) -> bool:
        """
        Checks if an entity ID represents a valid, active entity.

        Args:
            entity: The ID to check.

        Returns:
            True if the entity exists in this world, False otherwise.
        """
        self._switch()
        return bool(esper.entity_exists(entity))

    def add_component(self, entity: int, component: Any) -> None:
        """
        Attaches a single component to an existing entity.

        Publishes a `ComponentAddedEvent`.

        Args:
            entity: The target entity ID.
            component: The component instance to add.
        """
        self._switch()
        esper.add_component(entity, component)

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(ComponentAddedEvent(entity, type(component), component))

    def remove_component(self, entity: int, component_type: type[Any]) -> None:
        """
        Detaches a component of the specified type from an entity.

        Publishes a `ComponentRemovedEvent`. Safe to call if the component is missing.

        Args:
            entity: The target entity ID.
            component_type: The class of the component to remove.
        """
        self._switch()
        try:
            removed_component = esper.remove_component(entity, component_type)

            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(
                    ComponentRemovedEvent(entity, component_type, removed_component)
                )
        except KeyError:
            pass

    def get_component(self, entity: int, component_type: type[T]) -> T | None:
        """
        Retrieves a specific component from an entity.

        Args:
            entity: The entity ID.
            component_type: The class of the component to retrieve.

        Returns:
            The component instance if found, otherwise None.
        """
        self._switch()
        try:
            return esper.component_for_entity(entity, component_type)  # type: ignore[no-any-return]

        except KeyError:
            return None

    def try_get_component(self, entity: int, component_type: type[T]) -> T | None:
        """
        Safely retrieves a component without raising exceptions if missing.
        Optimized to avoid try-except overhead using `esper.try_component`.

        Args:
            entity: The entity ID.
            component_type: The class of the component to retrieve.

        Returns:
            The component instance if found, otherwise None.
        """
        self._switch()
        return esper.try_component(entity, component_type)  # type: ignore[no-any-return]

    def has_component(self, entity: int, component_type: type[Any]) -> bool:
        """
        Checks if an entity matches a specific component type.

        Args:
            entity: The entity ID.
            component_type: The component class to check for.

        Returns:
            True if the entity satisfies the component requirement, False otherwise.
        """
        self._switch()
        try:
            return bool(esper.has_component(entity, component_type))
        except KeyError:
            return False

    def get_components(self, component_type: type[T]) -> dict[int, T]:
        """
        Retrieves all instances of a specific component type across all entities.

        Args:
            component_type: The component class to query.

        Returns:
            A dictionary mapping Entity ID -> Component Instance.
        """
        self._switch()
        return {
            entity: component
            for entity, component in esper.get_component(component_type)
        }

    def get_all_entities(self) -> list[int]:
        """
        Retrieves all active entity IDs in this world.

        Returns:
            A list of all entity IDs.
        """
        return list(self._active_entities)

    def get_entities_with(self, *component_types: type[Any]) -> list[int]:
        """
        Finds entities that possess ALL of the specified component types.

        Args:
            *component_types: Variable list of component classes to direct the query.

        Returns:
            A list of matching entity IDs.
        """
        self._switch()
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
            *component_types: The component classes to query.

        Returns:
            A list of tuples, where each tuple contains:
            (Entity ID, (Component1, Component2, ...))
        """
        self._switch()
        return esper.get_components(*component_types)  # type: ignore[no-any-return]

    def get_all_components(self, entity: int) -> tuple[Any, ...]:
        """
        Retrieves every component attached to a specific entity.

        Args:
            entity: The entity ID.

        Returns:
            A tuple containing all component instances for the entity.
        """
        self._switch()
        try:
            return esper.components_for_entity(entity)  # type: ignore[no-any-return]
        except KeyError:
            return ()

    def add_system(self, system: "System") -> None:
        """
        Registers a System to run in this world.

        Injection:
            Sets `system.ecs_world` to this World instance.

        Args:
            system: The System instance to register.
        """
        self._switch()
        system.ecs_world = self
        system.initialize()
        esper.add_processor(system)

    def update(self, dt: float) -> None:
        """
        Advances the world state by one tick.

        Executes all registered Systems in priority order.

        Args:
            dt: Delta time in seconds since the last frame.
        """
        self._switch()
        esper.process(dt)

    def clear_database(self) -> None:
        """
        Removes all entities and components. Does NOT remove registered Systems.
        """
        self._switch()
        esper.clear_database()
        self._active_entities.clear()

    def destroy(self) -> None:
        """
        Completely tears down the world.

        clears the database, clears services, and removes the world context from `esper`.
        This is essential for memory management when unloading levels or closing the game.
        """
        self.clear_database()
        self.services.clear()
        try:
            # Esper cannot delete the currently active world, so we must switch safely.
            if esper.current_world == self.name:
                esper.switch_world("__garbage_collector__")

            esper.delete_world(self.name)
        except KeyError:
            pass


if TYPE_CHECKING:

    class ProcessorBase:
        """
        Type hint helper for Esper Processors.
        """

        def process(self, dt: float) -> None: ...

else:
    ProcessorBase = esper.Processor


class System(ProcessorBase):
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

        This method acts as a safeguard, ensuring the correct World context is active
        before passing control to the user-defined `update` logic.

        Args:
            dt: Delta time in seconds.
        """
        if hasattr(self, "ecs_world"):
            with self.ecs_world.context():
                self.update(self.ecs_world, dt)

    def initialize(self) -> None:
        """
        Lifecycle hook called when the system is first added to the World.

        Override this to perform setup tasks like subscribing to events.
        """
        pass

    def update(self, world: World, dt: float) -> None:
        """
        The core logic loop for the system.

        Must be implemented by subclasses.

        Args:
            world: The active ECS World instance.
            dt: Delta time in seconds.

        Raises:
            NotImplementedError: If not overridden by the subclass.
        """
        raise NotImplementedError
