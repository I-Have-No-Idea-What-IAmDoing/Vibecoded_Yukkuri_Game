from ...engine.ecs import System, World
from ..ai.navigation_service import NavigationService


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
            # We need to find the entity. If we don't have direct entity lookup by ID (ECS might support it),
            # we iterate? Hopefully world.get_component(id) works.
            # EntityID is just an int.

            if ai_state:
                # Clear requesting flag
                if ai_state.state_data:
                    ai_state.state_data["path_requesting"] = False

                if result.success:
                    ai_state.path = result.path
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
