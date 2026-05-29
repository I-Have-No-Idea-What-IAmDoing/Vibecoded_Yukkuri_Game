"""Tests for Tier B debugging improvements."""

import pygame
import pytest
import py_trees
from yukkuri_game.engine.exceptions import GameEngineError, MigrationError
from yukkuri_game.engine.scene_manager import SceneManager
from yukkuri_game.engine.scene import Scene
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.components import AIState
from yukkuri_game.engine.ecs import World


def test_exception_context_formatting() -> None:
    """Verifies that GameEngineError stringifies context metadata correctly."""
    err = GameEngineError(
        "Test message", context={"key": "test_key", "val": 42}
    )
    assert "Test message" in str(err)
    assert "Context: {key=test_key, val=42}" in str(err)


class DummyScene(Scene):
    """A dummy scene for testing injections."""

    INJECTIONS = {"money": int}

    def on_enter(self) -> None:
        """Called when scene is entered."""
        pass

    def on_exit(self) -> None:
        """Called when scene is exited."""
        pass

    def update(self, dt: float) -> None:
        """Updates scene logic."""
        pass

    def render(self, alpha: float) -> None:
        """Renders scene."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handles pygame input events."""
        pass


def test_scene_manager_migration_error_context() -> None:
    """Verifies that scene manager raises MigrationError on corrupted data."""
    manager = SceneManager()
    # Simulating corrupt persistent data: 'money' expected to hydrate from dict
    # but hydration fails due to structure mismatch or conversion failure.
    manager.set_global_data(
        "money", {"_version_": 1, "value": "corrupt_non_int"}
    )
    scene = DummyScene(None)  # type: ignore[arg-type]

    # Running scene setup to hydrate should trigger the exception wrapper
    with pytest.raises(MigrationError) as exc_info:
        manager.push(scene)

    err = exc_info.value
    assert err.context["key"] == "money"
    assert err.context["scene"] == "DummyScene"
    assert err.context["expected_type"] == "int"
    assert err.context["saved_version"] == 1


def test_behavior_system_active_node_path() -> None:
    """Verifies that BehaviorSystem active-node path resolves properly.

    Constructs a minimal py_trees tree manually and forces nodes into RUNNING
    so the path extractor can be tested without full game infrastructure.
    """
    world = World()

    # Register GameConfig service FIRST to satisfy BehaviorSystem.initialize()
    from yukkuri_game.config import (
        GameConfig,
        WorldSettings,
        TimeSettings,
        RulesFile,
    )

    world.services.register(
        GameConfig(
            world=WorldSettings(width=1000, height=1000),
            time=TimeSettings(),
            rules=RulesFile(),
        ),
        GameConfig,
    )

    system = BehaviorSystem()
    world.add_system(system)

    # Build a minimal 3-level tree manually
    root = py_trees.composites.Selector(name="Root Selector", memory=False)
    mid = py_trees.composites.Sequence(name="Wander Sequence", memory=False)
    leaf = py_trees.behaviours.Success(name="Wander")
    mid.add_child(leaf)
    root.add_child(mid)

    # Force all nodes into RUNNING to simulate an active execution path
    root.status = py_trees.common.Status.RUNNING
    mid.status = py_trees.common.Status.RUNNING
    leaf.status = py_trees.common.Status.RUNNING

    # Inject the tree directly (bypassing game startup)
    entity = world.create_entity(AIState())
    system.trees[entity] = py_trees.trees.BehaviourTree(root)
    system.trees[entity].root = root

    path = system.get_active_node_path(entity)
    assert "Root Selector" in path
    assert "Wander Sequence" in path
    assert "Wander" in path
    assert " → " in path

    world.destroy()


def test_behavior_system_active_node_path_returns_dash_for_unknown() -> None:
    """Verifies get_active_node_path returns '—' for an unknown entity."""
    world = World()

    from yukkuri_game.config import (
        GameConfig,
        WorldSettings,
        TimeSettings,
        RulesFile,
    )

    world.services.register(
        GameConfig(
            world=WorldSettings(width=1000, height=1000),
            time=TimeSettings(),
            rules=RulesFile(),
        ),
        GameConfig,
    )

    system = BehaviorSystem()
    world.add_system(system)

    path = system.get_active_node_path(9999)  # Non-existent entity
    assert path == "—"

    world.destroy()
