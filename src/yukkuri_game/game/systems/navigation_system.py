from ...engine.ecs import System, World
from ..ai.navigation_service import NavigationService
from ..yukkuri_components import AIState


class NavigationSystem(System):
    """
    System that processes asynchronous pathfinding results.
    """

    def update(self, world: World, dt: float) -> None:
        nav_service = world.services.try_get(NavigationService)
        if not nav_service:
            return

        results = nav_service.get_results()
        for result in results:
            # Update entity AIState
            ai_state = world.try_get_component(result.entity_id, AIState)

            if ai_state:
                # Clear requesting flag
                if ai_state.state_data:
                    ai_state.state_data["path_requesting"] = False

                if result.success:
                    ai_state.path = result.path

                    # Post-processing: Prune start node to prevent backtracking
                    # The navigation grid snaps start position to the nearest node, which might be "behind" the entity.
                    if ai_state.path and len(ai_state.path) > 1:
                        # We need Transform to check distance
                        # Check if Transform is imported? No, let's get it via world helper or assuming it's available
                        # We'll use world.try_get_component and manual dist calc to avoid pymunk dependency if not needed,
                        # but simpler to import pymunk/components if we can.
                        # Let's assume we can add imports at top of file separately or use raw maths.
                        from ..components import Transform

                        trans = world.try_get_component(result.entity_id, Transform)
                        if trans:
                            # Calculate distance squared manually to avoid PyMunk dep if not strictly needed
                            # path[0] is (x, y) tuple
                            px, py = ai_state.path[0]
                            dx = px - trans.x
                            dy = py - trans.y
                            dist_sq = dx * dx + dy * dy

                            # Grid step is 25. Diag is ~35.
                            # If within 30 units (900 sq), we assume it's the start node and skip.
                            if dist_sq < 900.0:
                                ai_state.path.pop(0)

                    # Signal that we have a path?
                    # The Behavior Tree will see ai_state.path is not None.
                    # We might want to store 'is_partial' info somewhere.
                    if result.is_partial:
                        # Maybe store in state_data
                        if ai_state.state_data is None:
                            ai_state.state_data = {}
                        ai_state.state_data["path_is_partial"] = True
                else:
                    # Path failure
                    # Behavior tree needs to know it failed.
                    # If we leave path as None, it might retry infinitely.
                    # We should probably set a 'failed_path' flag or similar.
                    # Or set path to empty list [] to indicate "no path found/direct move only".
                    # But [] implies arrived?
                    # Let's set a flag in state_data.
                    if ai_state.state_data is None:
                        ai_state.state_data = {}
                    ai_state.state_data["path_failed"] = True
