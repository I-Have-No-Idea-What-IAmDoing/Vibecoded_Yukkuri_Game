"""
Navigation System - Pathfinding Result Processor.
"""

from ...engine.ecs import System, World
from ..ai.navigation_service import NavigationService
from ..components import AIState
from ...engine.components import Transform

# Squared distance threshold for reaching a path node (30px ^ 2)
PATH_NODE_REACHED_THRESHOLD_SQ = 900.0


class NavigationSystem(System):
    """
    System that processes asynchronous pathfinding results.

    Retrieves completed paths from NavigationService and updates entity AIState.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the navigation system.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        nav_service = world.services.try_get(NavigationService)
        if not nav_service:
            return

        # Deterministic update (flushes queue if in deterministic mode)
        nav_service.update(world.time)

        results = nav_service.get_results()
        if not results:
            return

        for result in results:
            # Update entity AIState
            ai_state = world.try_get_component(result.entity_id, AIState)

            if not ai_state:
                continue

            # Clear requesting flag
            if ai_state.state_data:
                ai_state.state_data["path_requesting"] = False

            if result.success:
                ai_state.path = result.path

                # Prune start node to prevent backtracking.
                if ai_state.path and len(ai_state.path) > 1:
                    trans = world.try_get_component(result.entity_id, Transform)
                    if trans:
                        px, py = ai_state.path[0]
                        dx = px - trans.x
                        dy = py - trans.y
                        dist_sq = dx * dx + dy * dy

                        # Skip if within grid step distance.
                        if dist_sq < PATH_NODE_REACHED_THRESHOLD_SQ:
                            ai_state.path.pop(0)

                if result.is_partial:
                    if ai_state.state_data is None:
                        ai_state.state_data = {}
                    ai_state.state_data["path_is_partial"] = True
            else:
                if ai_state.state_data is None:
                    ai_state.state_data = {}
                ai_state.state_data["path_failed"] = True
