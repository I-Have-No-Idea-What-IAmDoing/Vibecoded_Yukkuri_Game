
import pytest
from src.yukkuri_game.game.ai.pathfinding import Pathfinding

def test_heuristic():
    """Test the heuristic calculation."""
    a = (0, 0)
    b = (3, 4)
    # Euclidean distance: sqrt(3^2 + 4^2) = 5
    assert Pathfinding.heuristic(a, b) == 5.0

def test_find_path_simple():
    """Test basic pathfinding on an empty grid."""
    start = (0, 0)
    goal = (100, 100)
    world_w = 200
    world_h = 200

    path = Pathfinding.find_path(start, goal, world_w, world_h)

    assert len(path) > 0
    assert path[0] == start
    assert path[-1] == goal

    # Check continuity (steps should be reasonably small, though the custom one steps by 50)
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i+1]
        dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        assert dist <= 75 # Diagonal step is ~70.7 (50 * sqrt(2))

def test_find_path_no_path():
    """Test pathfinding when destination is out of bounds (should return what?) or just bounds check."""
    # The current implementation snaps neighbors to bounds.
    # If start is (0,0) and goal is (300, 300) but world is (200, 200),
    # it might fail or clamp.
    # The current implementation:
    # if next_node is not valid, it's skipped.
    # if queue empty, it reconstructs path from closest visited.

    start = (0, 0)
    goal = (300, 300)
    world_w = 200
    world_h = 200

    path = Pathfinding.find_path(start, goal, world_w, world_h)

    # Should return a path that gets as close as possible
    assert len(path) > 0
    assert path[0] == start
    # It won't reach (300, 300), but should be near (200, 200)
    final_pos = path[-1]
    assert final_pos[0] <= world_w
    assert final_pos[1] <= world_h

def test_find_path_same_start_goal():
    start = (50, 50)
    goal = (50, 50)
    world_w = 200
    world_h = 200

    path = Pathfinding.find_path(start, goal, world_w, world_h)
    # Implementation detail: it might return [start, goal] or just [start]
    assert len(path) >= 1
    assert path[0] == start
    assert path[-1] == goal
