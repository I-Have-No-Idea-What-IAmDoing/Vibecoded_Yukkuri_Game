from yukkuri_game.game.ai.navigation_service import NavigationService


def test_find_path_simple():
    """Test basic pathfinding on an empty grid."""
    start = (0, 0)
    goal = (100, 100)
    world_w = 200
    world_h = 200

    nav = NavigationService(world_w, world_h, grid_step_size=50)

    path = nav.find_path(start, goal)

    assert len(path) > 0
    assert path[0] == start
    assert path[-1] == goal

    # Check continuity (steps should be reasonably small)
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i + 1]
        dist = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
        assert dist <= 75  # Diagonal step is ~70.7 (50 * sqrt(2))


def test_find_path_out_of_bounds():
    """Test pathfinding when destination is out of bounds (should return path to edge)"""
    start = (0, 0)
    goal = (300, 300)
    world_w = 200
    world_h = 200

    nav = NavigationService(world_w, world_h, grid_step_size=50)

    path = nav.find_path(start, goal)

    assert len(path) > 0
    assert path[0] == start

    # The goal is out of bounds, so it should clamp to the edge
    final_pos = path[-1]

    # Because of grid snapping, it might not be exactly 200, but close
    # The logic clamps grid indices.
    # Max X index for 200 / 50 = 4. Grid is 0-4.
    # Goal (300, 300) -> index (6, 6) -> clamped to (4, 4)
    # (4, 4) * 50 = (200, 200)

    assert final_pos[0] <= world_w
    assert final_pos[1] <= world_h


def test_find_path_same_start_goal():
    start = (50, 50)
    goal = (50, 50)
    world_w = 200
    world_h = 200

    nav = NavigationService(world_w, world_h, grid_step_size=50)

    path = nav.find_path(start, goal)

    # It might return [start] or [start, goal]
    assert len(path) >= 1
    assert path[0] == start
    assert path[-1] == goal


def test_obstacle_avoidance():
    """Test that pathfinding avoids obstacles."""
    start = (0, 0)
    goal = (200, 0)
    world_w = 300
    world_h = 100

    nav = NavigationService(world_w, world_h, grid_step_size=50)

    # Block (100, 0)
    nav.update_obstacle(100, 0, walkable=False)

    path = nav.find_path(start, goal)

    # Path should go around (100, 0)
    # (100, 0) shouldn't be in path

    for p in path:
        # Check if any point is close to the obstacle
        dist = ((p[0] - 100) ** 2 + (p[1] - 0) ** 2) ** 0.5
        assert dist > 1.0  # Should not be exactly at obstacle node
