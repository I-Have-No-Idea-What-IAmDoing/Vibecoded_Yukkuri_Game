"""
Entity Component System (ECS) Module.

This module provides a wrapper around the `esper` library to offer a more
structured and type-safe interface for managing entities and components.
It integrates with the `ServiceLocator` and `EventBus` for system-wide communication.
"""

import contextlib
import time
import uuid
from collections import deque
from collections.abc import Iterator, Callable
from functools import wraps
from typing import Any, TypeVar, cast, overload

import esper
from loguru import logger

from .event_bus import EventBus
from .events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    EntityDestroyedEvent,
)
from .service_locator import ServiceLocator

from abc import ABC, abstractmethod

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")


class Plugin(ABC):
    """
    Base class for engine and game plugins.

    Plugins allow modular registration of systems and services into the World.
    """

    @abstractmethod
    def register(self, world: "World") -> None:
        """
        Registers systems and services into the provided World.

        Args:
            world (World): The ECS World instance.
        """
        pass


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


class CommandBuffer:
    """
    Buffers ECS mutations to be applied at a safe time (e.g., end of frame).
    
    This prevents undefined behavior caused by adding/removing components
    or entities while a system is actively iterating over them.
    """

    def __init__(self, world: "World") -> None:
        self._world = world
        self._commands: list[Callable[[], None]] = []

    def create_entity(self, *components: Any) -> int:
        """
        Pre-allocates an entity ID immediately and queues the addition of its components.

        Returns:
            int: The ID of the newly created entity.
        """
        # Pre-allocate entity immediately to get a valid ID
        entity_id = int(esper.create_entity())
        self._world._active_entities.add(entity_id)
        
        if components:
            def _cmd() -> None:
                for component in components:
                    self._world.add_component(entity_id, component)
            self._commands.append(_cmd)

        return entity_id

    def destroy_entity(self, entity: int) -> None:
        """Queues an entity to be destroyed at the end of the frame."""
        def _cmd() -> None:
            if self._world.entity_exists(entity):
                self._world._destroy_entity_immediate(entity)
        self._commands.append(_cmd)

    def add_component(self, entity: int, component: Any) -> None:
        """Queues a component to be added to an entity at the end of the frame."""
        def _cmd() -> None:
            if self._world.entity_exists(entity):
                self._world.add_component(entity, component)
        self._commands.append(_cmd)

    def remove_component(self, entity: int, component_type: type[Any]) -> None:
        """Queues a component to be removed from an entity at the end of the frame."""
        if self._world.entity_exists(entity):
            if self._world.has_component(entity, component_type):
                comp = self._world.try_get_component(entity, component_type)
                if comp and hasattr(comp, "active"):
                    try:
                        comp.active = False
                    except AttributeError:
                        pass

        def _cmd() -> None:
            if self._world.entity_exists(entity):
                self._world.remove_component(entity, component_type)
        self._commands.append(_cmd)

    def apply_all(self) -> None:
        """Executes all queued commands and clears the buffer."""
        for cmd in self._commands:
            cmd()
        self._commands.clear()


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
        self._registered_systems: dict[type, System] = {}
        self._system_priorities: dict[type[System], int] = {}
        self._system_order: list[type[System]] = []
        self._sorted_systems: list[System] = []
        self._systems_dirty: bool = True
        self.commands: CommandBuffer = CommandBuffer(self)
        self._updating: bool = False
        self._seen_component_types: dict[str, type[Any]] = {}

        # Per-system timing support (enable with debug_timing = True).
        self.debug_timing: bool = False
        # Maps system class name -> rolling deque of frame times in ms.
        self._system_timings: dict[str, deque[float]] = {}
        self._timing_window: int = 60  # frames to average over

        # Register this world with esper's global context system.
        esper.switch_world(self.name)

    def _switch(self) -> None:
        """
        Switches the global esper context to this world's state.

        Optimized to avoid redundant context switches if this world is already active.
        """
        if esper.current_world != self.name:
            esper.switch_world(self.name)

    def _check_mutation(self) -> None:
        """
        Warns if a mutation is made while systems are updating.
        """
        if getattr(self, "_updating", False):
            logger.warning(
                "Direct mutation performed during World update! "
                "Use World.commands instead to avoid concurrent "
                "modification crashes."
            )

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
        from ..engine.services.time_service import TimeService

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
        self._check_mutation()
        entity_id = int(esper.create_entity(*components))
        self._active_entities.add(entity_id)

        comp_names = [type(c).__name__ for c in components]
        logger.debug(
            "Entity {} created: [{}]",
            entity_id,
            ", ".join(comp_names) if comp_names else "<no components>",
        )

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
        Defers removal of an entity and all its components from the world
        through the CommandBuffer to prevent mid-frame crashes.

        Args:
            entity (int): The ID of the entity to destroy.
        """
        self.commands.destroy_entity(entity)

    @ensure_context
    def _destroy_entity_immediate(self, entity: int) -> None:
        """
        Removes an entity and all its components immediately.
        Internal use only (called by CommandBuffer).

        Publishes an `EntityDestroyedEvent` before deletion. Safe to call even if
        the entity does not exist (no-op).

        Args:
            entity (int): The ID of the entity to destroy.
        """
        self._check_mutation()
        try:
            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(EntityDestroyedEvent(entity))

            logger.debug("Entity {} destroyed.", entity)
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
        self._check_mutation()

        # Safeguard duplicate namespace check
        comp_type = type(component)
        comp_name = comp_type.__name__
        comp_module = comp_type.__module__
        seen_type = self._seen_component_types.get(comp_name)
        if seen_type is not None and seen_type != comp_type:
            logger.error(
                "Duplicate component class name '{}' registered from "
                "different modules! Previous: {}.{}, Current: {}.{}. "
                "This will break ECS component lookups due to Python "
                "module dual-loading.",
                comp_name,
                seen_type.__module__,
                comp_name,
                comp_module,
                comp_name,
            )
        else:
            self._seen_component_types[comp_name] = comp_type

        esper.add_component(entity, component)

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(
                ComponentAddedEvent(entity, type(component), component)
            )

    @ensure_context
    def remove_component(self, entity: int, component_type: type[Any]) -> None:
        """
        Detaches a component of the specified type from an entity.

        Publishes a `ComponentRemovedEvent`. Safe to call if the component is missing.

        Args:
            entity (int): The target entity ID.
            component_type (type[Any]): The class of the component to remove.
        """
        self._check_mutation()
        try:
            removed_component = esper.component_for_entity(
                entity, component_type
            )
            esper.remove_component(entity, component_type)

            event_bus = self.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(
                    ComponentRemovedEvent(
                        entity, component_type, removed_component
                    )
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
        return dict(esper.get_component(component_type))

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

    @overload
    def get_components_tuple(
        self, __c1: type[T1]
    ) -> list[tuple[int, tuple[T1]]]: ...

    @overload
    def get_components_tuple(
        self, __c1: type[T1], __c2: type[T2]
    ) -> list[tuple[int, tuple[T1, T2]]]: ...

    @overload
    def get_components_tuple(
        self, __c1: type[T1], __c2: type[T2], __c3: type[T3]
    ) -> list[tuple[int, tuple[T1, T2, T3]]]: ...

    @overload
    def get_components_tuple(
        self, __c1: type[T1], __c2: type[T2], __c3: type[T3], __c4: type[T4]
    ) -> list[tuple[int, tuple[T1, T2, T3, T4]]]: ...

    @overload
    def get_components_tuple(
        self,
        __c1: type[T1],
        __c2: type[T2],
        __c3: type[T3],
        __c4: type[T4],
        __c5: type[T5],
    ) -> list[tuple[int, tuple[T1, T2, T3, T4, T5]]]: ...

    @overload
    def get_components_tuple(
        self, *component_types: type[Any]
    ) -> list[tuple[int, tuple[Any, ...]]]: ...

    def get_components_tuple(
        self, *component_types: type[Any]
    ) -> list[tuple[int, tuple[Any, ...]]]:
        """Efficiently retrieves entities and their components for a specific query signature.

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
    def add_system(self, system: "System", priority: int = 0) -> None:
        """
        Adds a system to the world.

        Args:
            system (System): The system instance.
            priority (int): Execution priority (higher = earlier). Defaults to 0.
        """
        system.ecs_world = self
        esper.add_processor(system, priority)
        self._registered_systems[type(system)] = system
        self._system_priorities[type(system)] = priority
        if type(system) not in self._system_order:
            self._system_order.append(type(system))
        self._systems_dirty = True

        if hasattr(system, "initialize"):
            system.initialize()

    @ensure_context
    def register_plugin(self, plugin: Plugin) -> None:
        """
        Registers a plugin into this world.

        Args:
            plugin (Plugin): The plugin instance to register.
        """
        plugin.register(self)

    def _topological_sort_systems(self) -> None:
        """
        Sorts registered systems using Kahn's algorithm.

        Enforces run_after and run_before dependencies, using priority
        (higher first) and insertion order as deterministic tie-breakers.

        Raises:
            CycleDependencyError: If a dependency cycle is detected.
        """
        from .exceptions import CycleDependencyError

        nodes = cast(list[type[System]], list(self._registered_systems.keys()))

        # Build name to type map for string-based dependency lookup
        name_to_type: dict[str, type[System]] = {n.__name__: n for n in nodes}

        # Build adjacency list (A runs before B) and compute in-degrees
        graph: dict[type[System], list[type[System]]] = {n: [] for n in nodes}
        in_degree: dict[type[System], int] = {n: 0 for n in nodes}

        for u in nodes:
            system_instance = self._registered_systems[u]

            # Explicit dependencies: u runs after dep -> dep runs before u
            for dep_raw in system_instance.run_after:
                dep = (
                    name_to_type.get(dep_raw)
                    if isinstance(dep_raw, str)
                    else dep_raw
                )
                if dep and dep in graph:
                    graph[dep].append(u)
                    in_degree[u] += 1

            # Explicit dependencies: u runs before dep -> u runs before dep
            for dep_raw in system_instance.run_before:
                dep = (
                    name_to_type.get(dep_raw)
                    if isinstance(dep_raw, str)
                    else dep_raw
                )
                if dep and dep in graph:
                    graph[u].append(dep)
                    in_degree[dep] += 1

        # Find all nodes with in-degree 0
        # Tie-breaker key: (-priority, registration_index)
        priority_map = self._system_priorities
        order_map = {
            sys_type: idx for idx, sys_type in enumerate(self._system_order)
        }

        def get_sort_key(sys_type: type[System]) -> tuple[int, int]:
            priority = priority_map.get(sys_type, 0)
            order_idx = order_map.get(sys_type, 0)
            return (-priority, order_idx)

        ready = [n for n in nodes if in_degree[n] == 0]
        ready.sort(key=get_sort_key)

        sorted_types: list[type[System]] = []

        while ready:
            u = ready.pop(0)
            sorted_types.append(u)

            for v in graph[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    ready.append(v)
            ready.sort(key=get_sort_key)

        if len(sorted_types) < len(nodes):
            cycle_nodes = [n.__name__ for n in nodes if in_degree[n] > 0]
            raise CycleDependencyError(
                f"Dependency cycle detected: {', '.join(cycle_nodes)}"
            )

        self._sorted_systems = [
            self._registered_systems[t] for t in sorted_types
        ]
        self._systems_dirty = False

    @ensure_context
    def update(self, dt: float) -> None:
        """
        Advances the world state by one tick.

        Executes all registered Systems in sorted execution order.
        When ``debug_timing`` is True, each system's execution time is
        recorded in a rolling window for display in the F3 overlay.

        Args:
            dt (float): Delta time in seconds since the last frame.
        """
        if self._systems_dirty:
            self._topological_sort_systems()

        self._updating = True
        try:
            if self.debug_timing:
                for system in self._sorted_systems:
                    t0 = time.perf_counter()
                    system.process(dt)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    name = type(system).__name__
                    if name not in self._system_timings:
                        self._system_timings[name] = deque(
                            maxlen=self._timing_window
                        )
                    self._system_timings[name].append(elapsed_ms)
            else:
                for system in self._sorted_systems:
                    system.process(dt)
        finally:
            self._updating = False

        self.commands.apply_all()

    def get_system_timings(self) -> dict[str, float]:
        """
        Returns average per-system frame time in milliseconds.

        Only populated when ``debug_timing`` is True.  Returns an empty
        dict if timing has not been enabled or no frames have been
        recorded yet.

        Returns:
            dict[str, float]: Mapping of system class name to average
                frame time in milliseconds, sorted descending by cost.
        """
        if not self._system_timings:
            return {}
        averages = {
            name: sum(times) / len(times)
            for name, times in self._system_timings.items()
            if times
        }
        return dict(
            sorted(averages.items(), key=lambda kv: kv[1], reverse=True)
        )

    @ensure_context
    def clear_database(self) -> None:
        """
        Removes all entities and components. Does NOT remove registered Systems.
        """
        esper.clear_database()
        self._active_entities.clear()

        event_bus = self.services.try_get(EventBus)
        if event_bus:
            from .events import WorldClearedEvent

            event_bus.publish(WorldClearedEvent())

    @ensure_context
    def destroy(self) -> None:
        """
        Completely tears down the world.

        Clears the database, clears services, and removes all systems.
        This is essential for memory management when unloading levels or closing the game.
        """
        self.clear_database()
        self.services.clear()
        # Remove all systems using our own tracker to avoid accessing
        # esper's private _processors attribute.
        for sys_type in list(self._registered_systems.keys()):
            self.remove_system(sys_type)
        self._registered_systems.clear()

        # Finally delete the world context
        try:
            esper.delete_world(self.name)
        except PermissionError:
            # Current world cannot be deleted, this is fine if we are tearing down
            pass

    @ensure_context
    def remove_system(self, system_type: type["System"]) -> None:
        """
        Removes a system from the world.

        Args:
            system_type (Type): The class of the system to remove.
        """
        esper.remove_processor(system_type)
        if system_type in self._registered_systems:
            del self._registered_systems[system_type]
        if system_type in self._system_priorities:
            del self._system_priorities[system_type]
        if system_type in self._system_order:
            self._system_order.remove(system_type)
        self._systems_dirty = True

    @ensure_context
    def get_system(self, system_type: type[T]) -> T:
        """
        Retrieves a registered system by its type.

        Args:
            system_type (Type[T]): The class of the system.

        Returns:
            T: The system instance.

        Raises:
            KeyError: If the system is not registered.
        """
        if system_type in self._registered_systems:
            return cast(T, self._registered_systems[system_type])
        raise KeyError(f"System of type {system_type.__name__} not found.")


class System(esper.Processor):
    """
    Base class for all ECS Systems.

    Systems hold game logic and operate on entities that possess specific components.
    Subclasses must implement the `update` method.

    Attributes:
        ecs_world (World): reference to the World this system belongs to. Injected automatically.
    """

    ecs_world: World
    run_after: list[type["System"] | str] = []
    run_before: list[type["System"] | str] = []

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
