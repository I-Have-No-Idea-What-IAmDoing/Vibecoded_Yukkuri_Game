"""
Unit tests for the Navigation Service unified grid with capabilities.
"""

import pytest
from yukkuri_game.game.ai.navigation_service import NavigationService, ObstacleType
from yukkuri_game.game.ai.navigation_constants import TraversalCapability


def _find_path_sync(
    nav: NavigationService,
    start: tuple[float, float],
    goal: tuple[float, float],
    capabilities: int = TraversalCapability.WALK,
) -> list[tuple[float, float]]:
    """Request a path and process it synchronously.

    Args:
        nav: NavigationService in deterministic_mode.
        start: Start position.
        goal: Goal position.
        capabilities: Traversal capability flags.

    Returns:
        The computed path, or [].
    """
    nav.request_path(
        entity_id=0, start=start, end=goal,
        capabilities=capabilities,
    )
    nav.update(0)
    results = nav.get_results()
    if results and results[0].success:
        return results[0].path
    return []


class TestNavigationServiceDualGrids:
    """Tests for navigation grid capabilities (Unified Grid)."""

    @pytest.fixture
    def nav(self):
        service = NavigationService(1000, 1000, grid_step_size=50, deterministic_mode=True)
        yield service
        service.shutdown()

    def test_initialization_creates_grid(self, nav):
        """Verify unified grid is created."""
        print("DEBUG: Start Init Test")
        assert nav.grid is not None
        # Verify default state (Walkable and Flyable)
        assert nav.grid.is_walkable(0, 0, TraversalCapability.WALK)
        assert nav.grid.is_walkable(0, 0, TraversalCapability.FLY)

    def test_low_obstacle_only_blocks_ground(self, nav):
        """LOW obstacles should only block WALK, not FLY."""
        # Place a low obstacle
        nav.update_obstacle_rect(
            100.0, 100.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.LOW
        )

        gx, gy = 2, 2  # 100 / 50 = 2
        # Ground (WALK) blocked
        assert not nav.grid.is_walkable(gx, gy, TraversalCapability.WALK)
        # Air (FLY) unaffected
        assert nav.grid.is_walkable(gx, gy, TraversalCapability.FLY)

    def test_high_obstacle_blocks_both(self, nav):
        """HIGH obstacles should block both WALK and FLY."""
        nav.update_obstacle_rect(
            200.0, 200.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.HIGH
        )

        gx, gy = 4, 4
        assert not nav.grid.is_walkable(gx, gy, TraversalCapability.WALK)
        assert not nav.grid.is_walkable(gx, gy, TraversalCapability.FLY)

    def test_find_path_ground_blocked_by_low_obstacle(self, nav):
        """Ground path should be blocked by low obstacles."""
        nav.update_obstacle_rect(
            100.0, 0.0, 50.0, 50.0, walkable=False,
            obstacle_type=ObstacleType.LOW,
        )
        nav.update(0)  # rebuild graph after obstacle

        path = _find_path_sync(
            nav, (0.0, 0.0), (200.0, 0.0),
            capabilities=TraversalCapability.WALK,
        )

        assert path is not None
        assert len(path) > 0

        # Check if any point is exactly at the blockage.
        blocked = False
        for px, py in path:
            if abs(px - 100.0) < 10.0 and abs(py - 0.0) < 10.0:
                blocked = True
        assert not blocked, "Path went through obstacle"

    def test_find_path_air_ignores_low_obstacle(self, nav):
        """Air path should ignore low obstacles."""
        nav.update_obstacle_rect(
            100.0, 0.0, 50.0, 50.0, walkable=False,
            obstacle_type=ObstacleType.LOW,
        )
        nav.update(0)  # rebuild graph after obstacle

        path = _find_path_sync(
            nav, (0.0, 0.0), (200.0, 0.0),
            capabilities=TraversalCapability.FLY,
        )

        assert path is not None
        assert len(path) > 0
        
    def test_reset_clears_grid(self, nav):
        """Reset should clear grid."""
        nav.update_obstacle_rect(
            100.0, 100.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.HIGH
        )
        nav.reset()

        gx, gy = 2, 2
        assert nav.grid.is_walkable(gx, gy, TraversalCapability.WALK)
        assert nav.grid.is_walkable(gx, gy, TraversalCapability.FLY)

    def test_obstacle_rect_no_inflation(self, nav):
        """Placing an obstacle must not inflate its size by double-compensation."""
        # Place obstacle at 100.0, 100.0 with size 50 x 50.
        # Spans [75, 125] on X and Y, occupying grid cell (2, 2) exactly.
        nav.update_obstacle_rect(
            100.0, 100.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.HIGH
        )
        
        # Cell (2, 2) should be blocked.
        assert not nav.grid.is_walkable(2, 2, TraversalCapability.WALK)
        # Neighboring cells must remain walkable.
        assert nav.grid.is_walkable(3, 2, TraversalCapability.WALK)
        assert nav.grid.is_walkable(2, 3, TraversalCapability.WALK)



