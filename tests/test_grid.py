"""
Tests for the item placement and collision system.
"""

import pytest

from game.core.ecs.entity import Entity
from game.core.sim.grid import Grid


def test_item_placement_and_collision():
    """
    Tests that item placement and collision detection works correctly.
    """
    grid = Grid(10, 10)
    item1 = Entity(1)
    item2 = Entity(2)

    # Place the first item
    assert grid.can_place(0, 0, 2, 2)
    grid.place(item1, 0, 0, 2, 2)

    # Attempt to place the second item in an overlapping location
    assert not grid.can_place(1, 1, 2, 2)

    # Attempt to place the second item in a valid location
    assert grid.can_place(3, 3, 2, 2)
    grid.place(item2, 3, 3, 2, 2)

    # Attempt to place an item out of bounds
    assert not grid.can_place(9, 9, 2, 2)


def test_remove_item():
    """Tests that items can be removed from the grid."""
    grid = Grid(10, 10)
    item = Entity(1)

    grid.place(item, 0, 0, 2, 2)
    assert not grid.can_place(0, 0, 1, 1)

    grid.remove(item.entity_id)
    assert grid.can_place(0, 0, 1, 1)
