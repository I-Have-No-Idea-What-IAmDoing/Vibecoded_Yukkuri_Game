"""Tests HPA behavior for flying units across clusters."""

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


class TestHPAFlying:
    """Tests HPA behavior for flying units across clusters."""

    def test_fly_across_unwalkable_boundary(self):
        """
        Verify HPA graph is built separately for WALK and FLY capabilities.

        Scenario:
        - Create a wall at x=7 (boundary between cluster 0,0 and 1,0).
        - Wall is LOW obstacle (blocks Walk, allows Fly).

        Expected:
        - WALK graph: No edges between Cluster 0 and 1 (blocked).
        - FLY graph: Edges exist between Cluster 0 and 1 (traversable).
        - Walk path fails.
        - Fly path succeeds using HPA (not fallback A*).
        """
        nav = NavigationService(
            world_width=500,
            world_height=500,
            grid_step_size=25,
            deterministic_mode=True,
        )

        # Block x=7 for all y with LOW obstacle (Walk blocked, Fly allowed)
        for y in range(21):
            nav.update_obstacle_rect(
                7 * 25, y * 25, 25, 25, walkable=False, obstacle_type=ObstacleType.LOW
            )

        nav.update(0)

        # 1. Verify Walk Path fails
        path_walk = _find_path_sync(
            nav, (0, 0), (250, 0),
            capabilities=TraversalCapability.WALK,
        )
        assert len(path_walk) == 0, "Walk path should be blocked"

        # 2. Verify Fly Path succeeds
        path_fly = _find_path_sync(
            nav, (0, 0), (250, 0),
            capabilities=TraversalCapability.FLY,
        )
        assert len(path_fly) > 0, "Fly path should be found"

        # 3. Verify WALK graph has NO edges between Cluster 0 and 1
        walk_graph = nav.get_graph(TraversalCapability.WALK)
        c0_walk = walk_graph.clusters.get((0, 0))
        c1_walk = walk_graph.clusters.get((1, 0))
        assert c0_walk is not None
        assert c1_walk is not None

        walk_connections = 0
        for node_id in c0_walk.nodes.values():
            node = walk_graph.graph_nodes[node_id]
            for edge in node.edges:
                target_node = walk_graph.graph_nodes.get(edge.target_node_id)
                if target_node and target_node.cluster_coords == (1, 0):
                    walk_connections += 1

        assert (
            walk_connections == 0
        ), "WALK graph should NOT have edges if WALK is blocked"

        # 4. Verify FLY graph HAS edges between Cluster 0 and 1
        fly_graph = nav.get_graph(TraversalCapability.FLY)
        c0_fly = fly_graph.clusters.get((0, 0))
        c1_fly = fly_graph.clusters.get((1, 0))
        assert c0_fly is not None
        assert c1_fly is not None

        fly_connections = 0
        for node_id in c0_fly.nodes.values():
            node = fly_graph.graph_nodes[node_id]
            for edge in node.edges:
                target_node = fly_graph.graph_nodes.get(edge.target_node_id)
                if target_node and target_node.cluster_coords == (1, 0):
                    fly_connections += 1

        assert fly_connections > 0, "FLY graph SHOULD have edges since FLY is allowed"

        nav.shutdown()
