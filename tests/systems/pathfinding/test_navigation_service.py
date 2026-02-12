"""Tests for NavigationService pathfinding via the async API."""

from yukkuri_game.game.ai.navigation_service import (
    NavigationService,
    ObstacleType,
)


def _find_path_sync(
    nav: NavigationService,
    start: tuple[float, float],
    goal: tuple[float, float],
) -> list[tuple[float, float]]:
    """Helper: request a path and process it synchronously.

    Uses deterministic mode to process the request inline.

    Args:
        nav: A NavigationService in deterministic_mode.
        start: World-coordinate start position.
        goal: World-coordinate goal position.

    Returns:
        The computed path as world-coordinate tuples, or [].
    """
    nav.request_path(entity_id=0, start=start, end=goal)
    nav.update(0)
    results = nav.get_results()
    if results and results[0].success:
        return results[0].path
    return []


def test_find_path_simple() -> None:
    """Test basic pathfinding on an empty grid."""
    start = (0.0, 0.0)
    goal = (100.0, 100.0)

    nav = NavigationService(200, 200, grid_step_size=50, deterministic_mode=True)
    try:
        path = _find_path_sync(nav, start, goal)

        assert len(path) > 0
        assert path[0] == start
        assert path[-1] == goal
    finally:
        nav.shutdown()


def test_find_path_out_of_bounds() -> None:
    """Test pathfinding when destination is out of bounds."""
    start = (0.0, 0.0)
    goal = (300.0, 300.0)
    world_w = 200
    world_h = 200

    nav = NavigationService(
        world_w, world_h, grid_step_size=50, deterministic_mode=True
    )
    try:
        path = _find_path_sync(nav, start, goal)

        assert len(path) > 0
        assert path[0] == start

        # Goal is out of bounds → clamped to grid edge.
        final_pos = path[-1]
        assert final_pos[0] <= world_w
        assert final_pos[1] <= world_h
    finally:
        nav.shutdown()


def test_find_path_same_start_goal() -> None:
    """Trivial path: start == goal."""
    start = (50.0, 50.0)
    goal = (50.0, 50.0)

    nav = NavigationService(200, 200, grid_step_size=50, deterministic_mode=True)
    try:
        path = _find_path_sync(nav, start, goal)

        assert len(path) >= 1
        assert path[0] == start
        assert path[-1] == goal
    finally:
        nav.shutdown()


def test_obstacle_avoidance() -> None:
    """Test that pathfinding avoids obstacles."""
    start = (0.0, 0.0)
    goal = (200.0, 0.0)

    nav = NavigationService(300, 100, grid_step_size=50, deterministic_mode=True)
    try:
        # Block (100, 0)
        nav.update_obstacle_rect(100, 0, 50, 50, walkable=False)
        nav.update(0)  # rebuild graph after obstacle

        path = _find_path_sync(nav, start, goal)

        # Path should go around (100, 0)
        for p in path:
            dist = ((p[0] - 100) ** 2 + (p[1] - 0) ** 2) ** 0.5
            assert dist > 1.0, "Path should not pass through obstacle"
    finally:
        nav.shutdown()
