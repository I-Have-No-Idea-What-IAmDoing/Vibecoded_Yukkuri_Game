"""
Tests for declarative component persistence and transient field support.
"""

from dataclasses import dataclass
from dataclasses import field
import pytest
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.ecs import System
from yukkuri_game.engine.persistence_registry import persistent
from yukkuri_game.engine.persistence_registry import PersistenceRegistry
from yukkuri_game.engine.serializer import WorldSerializer
from yukkuri_game.engine.components import Persistable
from yukkuri_game.engine.components import StableIDComponent
from loguru import logger


@persistent
@dataclass
class DummyPersistentComponent:
    """
    Dummy component for testing persistent decoration and transient fields.
    """

    value: int = 42
    transient_val: str = field(
        default="hello", metadata={"persistent": False}
    )


class DummyMutationSystem(System):
    """
    A system that performs immediate mutation during process.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Processes the system, performing a direct mutation.

        Args:
            world: The ECS World instance.
            dt: Delta time.
        """
        # Trigger immediate mutation
        world.create_entity()


class DummyLifecycleService:
    """
    Dummy service to test service locator lifecycle management.
    """

    def __init__(self) -> None:
        self.initialized: bool = False
        self.shutdown_called: bool = False

    def initialize(self) -> None:
        """Initializes the service."""
        self.initialized = True

    def shutdown(self) -> None:
        """Shuts down the service."""
        self.shutdown_called = True


def test_persistence_registration() -> None:
    """
    Verify that @persistent correctly registers component classes.
    """
    registered = PersistenceRegistry.get_registered_components()
    assert DummyPersistentComponent in registered


def test_transient_field_exclusion() -> None:
    """
    Verify that fields with persistent=False metadata are excluded.
    """
    world = World()
    entity = world.create_entity()
    world.add_component(entity, Persistable())
    world.add_component(entity, StableIDComponent(id=42))

    comp = DummyPersistentComponent(value=10, transient_val="changed")
    world.add_component(entity, comp)

    serializer = WorldSerializer(
        world,
        [
            Persistable,
            StableIDComponent,
            DummyPersistentComponent,
        ],
    )
    serialized = serializer.serialize_entity(entity)

    assert serialized is not None
    comp_data = serialized["components"].get("DummyPersistentComponent")
    assert comp_data is not None

    # 'value' should be serialized, but 'transient_val' should be excluded
    assert comp_data["value"] == 10
    assert "transient_val" not in comp_data


def test_transient_field_default_loading() -> None:
    """
    Verify that transient fields default to their class definition default on load.
    """
    world = World()
    entity = world.create_entity()
    world.add_component(entity, Persistable())
    world.add_component(entity, StableIDComponent(id=42))

    comp = DummyPersistentComponent(value=10, transient_val="changed")
    world.add_component(entity, comp)

    serializer = WorldSerializer(
        world,
        [
            Persistable,
            StableIDComponent,
            DummyPersistentComponent,
        ],
    )
    serialized = serializer.serialize_entity(entity)

    assert serialized is not None

    # Load into a clean world
    clean_world = World()
    clean_serializer = WorldSerializer(
        clean_world,
        [
            Persistable,
            StableIDComponent,
            DummyPersistentComponent,
        ],
    )
    clean_serializer.load_from_data([serialized])

    entities = clean_world.get_all_entities()
    assert len(entities) == 1
    loaded_entity = entities[0]

    loaded_comp = clean_world.get_component(
        loaded_entity, DummyPersistentComponent
    )
    assert loaded_comp.value == 10
    # transient_val should have loaded as the default "hello", not "changed"
    assert loaded_comp.transient_val == "hello"


def test_mutation_safety_warning(caplog: pytest.LogCaptureFixture) -> None:
    """
    Verify that immediate ecs mutations during update emit log warnings.
    """
    world = World()
    world.add_system(DummyMutationSystem())

    caplog.handler.setLevel("WARNING")
    sink_id = logger.add(caplog.handler, level="WARNING", format="{message}")
    try:
        world.update(0.1)
    finally:
        logger.remove(sink_id)

    # Check that warning about direct mutation was logged
    warnings = [
        rec.message
        for rec in caplog.records
        if "Direct mutation performed" in rec.message
    ]
    assert len(warnings) > 0


def test_service_lifecycle_locator() -> None:
    """
    Verify that ServiceLocator manages service initialization and shutdown.
    """
    world = World()
    service = DummyLifecycleService()

    # Register should call initialize
    world.services.register(service)
    assert service.initialized is True
    assert service.shutdown_called is False

    # Clear should call shutdown
    world.services.clear()
    assert service.shutdown_called is True
