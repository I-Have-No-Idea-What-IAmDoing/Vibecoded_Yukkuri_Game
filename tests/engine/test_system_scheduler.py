"""
Tests for the ECS System Execution Scheduler and Topological Sorting.
"""

from typing import Type

import pytest

from yukkuri_game.engine.ecs import System
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.exceptions import CycleDependencyError


class SystemA(System):
    """Mock System A."""

    def update(self, world: World, dt: float) -> None:
        """Updates the system.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        pass


class SystemB(System):
    """Mock System B."""

    def update(self, world: World, dt: float) -> None:
        """Updates the system.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        pass


class SystemC(System):
    """Mock System C."""

    def update(self, world: World, dt: float) -> None:
        """Updates the system.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        pass


def test_topological_sort_linear() -> None:
    """Verifies that sequential run_after dependencies sort correctly."""
    world = World()

    # Define linear dependencies: C runs after B, B runs after A.
    # Expected order: A, B, C
    class MockA(SystemA):
        """Mock system A."""
        pass

    class MockB(SystemB):
        """Mock system B."""
        run_after = [MockA]

    class MockC(SystemC):
        """Mock system C."""
        run_after = [MockB]

    world.add_system(MockC())
    world.add_system(MockA())
    world.add_system(MockB())

    # Trigger topological sort via update or direct call
    world.update(0.1)

    assert [type(sys) for sys in world._sorted_systems] == [MockA, MockB, MockC]


def test_topological_sort_run_before() -> None:
    """Verifies that run_before dependencies sort correctly."""
    world = World()

    # Define: A runs before B, B runs before C.
    # Expected order: A, B, C
    class MockC(SystemC):
        """Mock system C."""
        pass

    class MockB(SystemB):
        """Mock system B."""
        run_before = [MockC]

    class MockA(SystemA):
        """Mock system A."""
        run_before = [MockB]

    world.add_system(MockC())
    world.add_system(MockB())
    world.add_system(MockA())

    world.update(0.1)

    assert [type(sys) for sys in world._sorted_systems] == [MockA, MockB, MockC]


def test_topological_sort_tie_break_priority() -> None:
    """Verifies that priority breaks ties for systems without dependencies."""
    world = World()

    # All three systems have no dependencies.
    # Priority: MockB (10) > MockC (5) > MockA (0).
    # Expected order: MockB, MockC, MockA
    class MockA(SystemA):
        """Mock system A."""
        pass

    class MockB(SystemB):
        """Mock system B."""
        pass

    class MockC(SystemC):
        """Mock system C."""
        pass

    world.add_system(MockA(), priority=0)
    world.add_system(MockB(), priority=10)
    world.add_system(MockC(), priority=5)

    world.update(0.1)

    assert [type(sys) for sys in world._sorted_systems] == [MockB, MockC, MockA]


def test_topological_sort_tie_break_registration() -> None:
    """Verifies that registration order breaks ties when priorities are equal."""
    world = World()

    class MockA(SystemA):
        """Mock system A."""
        pass

    class MockB(SystemB):
        """Mock system B."""
        pass

    class MockC(SystemC):
        """Mock system C."""
        pass

    # Registered C, A, then B. All have same priority.
    # Expected order: MockC, MockA, MockB
    world.add_system(MockC())
    world.add_system(MockA())
    world.add_system(MockB())

    world.update(0.1)

    assert [type(sys) for sys in world._sorted_systems] == [MockC, MockA, MockB]


def test_cycle_dependency_raises_error() -> None:
    """Verifies that dependency cycles raise CycleDependencyError."""
    world = World()

    # Define a cycle: A runs after B, B runs after A.
    class MockA(SystemA):
        """Mock system A."""
        pass

    class MockB(SystemB):
        """Mock system B."""
        run_after = [MockA]

    MockA.run_after = [MockB]  # type: ignore

    world.add_system(MockA())
    world.add_system(MockB())

    with pytest.raises(CycleDependencyError) as exc_info:
        world.update(0.1)

    assert "Dependency cycle detected" in str(exc_info.value)
