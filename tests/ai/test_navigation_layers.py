"""
Unit tests for the Navigation Service unified grid with capabilities.
"""

import pytest
from yukkuri_game.game.ai.navigation_service import NavigationService, ObstacleType
from yukkuri_game.game.ai.navigation_constants import TraversalCapability


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
        # Block a cell with LOW obstacle at (100, 0) which is grid (2, 0)
        nav.update_obstacle_rect(
            100.0, 0.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.LOW
        )

        # Try to path from (0,0) to (200,0)
        path = nav.find_path((0.0, 0.0), (200.0, 0.0), can_fly=False)

        # Path should exist but avoid the blocked cell
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
        # Block with LOW obstacle at (100, 0)
        nav.update_obstacle_rect(
            100.0, 0.0, 50.0, 50.0, walkable=False, obstacle_type=ObstacleType.LOW
        )

        # Find path as flying unit
        path = nav.find_path((0.0, 0.0), (200.0, 0.0), can_fly=True)

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


