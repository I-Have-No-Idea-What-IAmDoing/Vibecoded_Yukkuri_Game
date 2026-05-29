"""
Navigation Controller Utility.

Provides a stateless helper class for entities to execute navigation tasks,
including line-of-sight checks, async path request queuing, takeoff management,
and pursuit drift calculations.
"""

from typing import TYPE_CHECKING, cast
import pymunk
from py_trees.common import Status

from yukkuri_game.engine.types import EntityID
from yukkuri_game.engine.components import (
    Flight,
    FlightState,
    MovementController,
    PhysicsBody,
    Transform,
)
from yukkuri_game.game.components import (
    AIState,
    MoveCommand,
    Needs,
)
from yukkuri_game.game.ai.navigation_constants import TraversalCapability
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.engine.protocols import IPhysicsService

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World

MIN_TAKEOFF_STAMINA = 20.0


class NavigationController:
    """
    Stateless utility handling HPA* path requests and close-range direct steering.
    """

    @staticmethod
    def _cleanup_nav_state(ai: AIState) -> None:
        """
        Cleans up transient path request and destination data from AIState.
        """
        if ai.state_data:
            ai.state_data.pop("path_requesting", None)
            ai.state_data.pop("path_destination", None)
            ai.state_data.pop("pursuit_repath", None)
            ai.state_data.pop("stuck_count", None)

    @staticmethod
    def navigate_to(
        world: "World",
        entity_id: int,
        target_pos: pymunk.Vec2d,
        target_entity_id: int | None,
        speed: float,
        acceptance_radius: float,
    ) -> Status:
        """
        Navigates an entity towards a target position using direct or path modes.

        Args:
            world (World): The ECS World instance.
            entity_id (int): The ID of the navigating entity.
            target_pos (pymunk.Vec2d): Target position coordinates.
            target_entity_id (int | None): Optional target entity ID.
            speed (float): Desired movement speed.
            acceptance_radius (float): Stopping distance threshold.

        Returns:
            Status: The py_trees Status (RUNNING, SUCCESS, FAILURE).
        """
        ai = world.try_get_component(entity_id, AIState)
        trans = world.try_get_component(entity_id, Transform)
        needs = world.try_get_component(entity_id, Needs)
        controller = world.try_get_component(entity_id, MovementController)

        if ai is None or trans is None or needs is None or controller is None:
            return Status.FAILURE

        # Handle too many stuck occurrences
        if ai.state_data and ai.state_data.get("stuck_count", 0) >= 3:
            from loguru import logger
            logger.warning(
                f"Entity {entity_id} failed navigation to "
                f"({target_pos.x:.1f}, {target_pos.y:.1f}) "
                f"after getting stuck 3 times."
            )
            controller.target_velocity = pymunk.Vec2d(0, 0)
            ai.path = None
            NavigationController._cleanup_nav_state(ai)
            if world.has_component(entity_id, MoveCommand):
                world.commands.remove_component(entity_id, MoveCommand)
            return Status.FAILURE

        # Get TimeService for physics time calculations
        from yukkuri_game.engine.services.time_service import TimeService

        services = getattr(world, "services", None)
        time_service = (
            services.try_get(TimeService) if services else None
        )
        raw_scale = (
            getattr(time_service, "game_delta_multiplier", 60.0)
            if time_service
            else 60.0
        )
        scale = (
            raw_scale
            if isinstance(raw_scale, (int, float))
            else 60.0
        )
        raw_time = getattr(world, "time", 0.0)
        w_time = (
            raw_time
            if isinstance(raw_time, (int, float))
            else 0.0
        )
        physics_time = w_time / max(0.1, scale)

        # Handle failed target validation
        if target_entity_id is not None:
            if target_entity_id in ai.failed_targets and not ai.manual_override:
                controller.target_velocity = pymunk.Vec2d(0, 0)
                if world.has_component(entity_id, MoveCommand):
                    world.commands.remove_component(entity_id, MoveCommand)
                return Status.FAILURE

        current_pos = pymunk.Vec2d(trans.x, trans.y)

        # Calculate dynamic physical acceptance radius to prevent getting stuck
        # due to body collisions.
        eff_accept_rad = acceptance_radius
        if target_entity_id is not None:
            self_phys = world.try_get_component(entity_id, PhysicsBody)
            target_phys = world.try_get_component(
                target_entity_id, PhysicsBody
            )
            if self_phys and target_phys:
                self_radius = 0.0
                target_radius = 0.0
                for shape in self_phys.body.shapes:
                    if not shape.sensor and hasattr(shape, "radius"):
                        self_radius = shape.radius
                        break
                for shape in target_phys.body.shapes:
                    if not shape.sensor and hasattr(shape, "radius"):
                        target_radius = shape.radius
                        break
                min_dist = self_radius + target_radius
                if min_dist > 0.0:
                    # Provide 5px buffer to ensure arrival is triggered reliably
                    eff_accept_rad = max(acceptance_radius, min_dist + 5.0)

        # Close-Range / Line-of-Sight Optimization
        is_visible = target_entity_id is None or (
            target_entity_id in ai.visible_entities
        )

        if (is_visible or ai.manual_override) and target_pos:
            dist_to_target = (target_pos - current_pos).length
            use_direct_steering = False

            if dist_to_target < 400.0:
                physics_sys = world.services.try_get(IPhysicsService)
                if physics_sys and hasattr(physics_sys, "space"):
                    space = physics_sys.space
                    filter_ = pymunk.ShapeFilter(
                        mask=pymunk.ShapeFilter.ALL_MASKS(),
                        group=entity_id,
                    )
                    hit = space.segment_query_first(
                        current_pos, target_pos, 1.0, filter_
                    )
                    if hit is None:
                        use_direct_steering = True
                    elif hit.shape and target_entity_id is not None:
                        target_phys = world.try_get_component(
                            target_entity_id, PhysicsBody
                        )
                        if target_phys and hit.shape.body == target_phys.body:
                            use_direct_steering = True
                else:
                    if dist_to_target < 150.0:
                        use_direct_steering = True

            if use_direct_steering:
                if dist_to_target < eff_accept_rad:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    ai.path = None
                    NavigationController._cleanup_nav_state(ai)
                    if world.has_component(entity_id, MoveCommand):
                        world.commands.remove_component(entity_id, MoveCommand)
                    return Status.SUCCESS

                speed_modifier = 1.0
                if needs.energy < 30:
                    speed_modifier = 0.5

                world.commands.add_component(
                    entity_id,
                    MoveCommand(
                        target_pos=target_pos,
                        target_entity_id=(
                            cast(EntityID, target_entity_id)
                            if target_entity_id is not None
                            else None
                        ),
                        speed_multiplier=speed_modifier,
                        priority=2,
                        acceptance_radius=eff_accept_rad,
                    ),
                )

                if ai.path:
                    ai.path = None

                return Status.RUNNING

        if target_pos:
            dist_sq = (target_pos - current_pos).length_squared
            if dist_sq < eff_accept_rad * eff_accept_rad:
                controller.target_velocity = pymunk.Vec2d(0, 0)
                ai.path = None
                NavigationController._cleanup_nav_state(ai)
                if world.has_component(entity_id, MoveCommand):
                    world.commands.remove_component(entity_id, MoveCommand)
                return Status.SUCCESS

        # Pathfinding (Async)
        if ai.path is None or not ai.path:
            state_data = ai.state_data if ai.state_data else {}
            is_requesting = state_data.get("path_requesting", False)
            path_failed = state_data.get("path_failed", False)

            if path_failed:
                state_data["path_requesting"] = False
                if "path_failed" in state_data:
                    del state_data["path_failed"]
                if "path_request_time" in state_data:
                    del state_data["path_request_time"]
                if "path_destination" in state_data:
                    del state_data["path_destination"]
                ai.state_data = state_data

                if target_entity_id is not None:
                    ai.failed_targets.add(cast(EntityID, target_entity_id))

                if world.has_component(entity_id, MoveCommand):
                    world.commands.remove_component(entity_id, MoveCommand)

                return Status.FAILURE

            if is_requesting:
                request_timestamp = state_data.get("path_request_time", 0.0)
                if (
                    request_timestamp > physics_time
                    or (physics_time - request_timestamp) > 2.0
                ):
                    state_data["path_requesting"] = False
                else:
                    return Status.RUNNING

            nav_service = world.services.try_get(NavigationService)
            if nav_service:
                capabilities = TraversalCapability.WALK
                flight_comp = world.try_get_component(entity_id, Flight)
                if flight_comp and flight_comp.stamina > MIN_TAKEOFF_STAMINA:
                    capabilities |= TraversalCapability.FLY
                    if flight_comp.state == FlightState.GROUNDED:
                        flight_comp.state = FlightState.TAKEOFF

                priority = 2
                if ai.state_data and ai.state_data.get(
                    "pursuit_repath", False
                ):
                    priority = 0
                    ai.state_data["pursuit_repath"] = False

                nav_service.request_path(
                    entity_id,
                    (trans.x, trans.y),
                    (target_pos.x, target_pos.y),
                    capabilities=capabilities,
                    priority=priority,
                    timestamp=world.time,
                )

                if ai.state_data is None:
                    ai.state_data = {}
                ai.state_data["path_requesting"] = True
                ai.state_data["path_request_time"] = physics_time
                ai.state_data["path_destination"] = (
                    target_pos.x,
                    target_pos.y,
                )
                if "path_failed" in ai.state_data:
                    del ai.state_data["path_failed"]

                return Status.RUNNING

        # Drift Detection
        if ai.path and target_pos:
            is_visible = target_entity_id is None or (
                target_entity_id in ai.visible_entities
            )
            if is_visible:
                if ai.state_data is None:
                    ai.state_data = {}
                ai.state_data["last_known_x"] = target_pos.x
                ai.state_data["last_known_y"] = target_pos.y

                path_dest = ai.state_data.get("path_destination")
                if path_dest:
                    drift_threshold_sq = 2500.0
                    target_phys = None
                    if target_entity_id is not None:
                        target_phys = world.try_get_component(
                            target_entity_id, PhysicsBody
                        )
                    if target_phys and target_phys.body:
                        t_speed = target_phys.body.velocity.length
                        val = max(20.0, 50.0 - (t_speed * 0.3))
                        drift_threshold_sq = val * val

                    drift_sq = (
                        target_pos - pymunk.Vec2d(*path_dest)
                    ).length_squared
                    if drift_sq > drift_threshold_sq:
                        last_repath_time = ai.state_data.get(
                            "last_repath_time", 0.0
                        )
                        if (
                            last_repath_time > physics_time
                            or (physics_time - last_repath_time) > 0.5
                        ):
                            ai.path = None
                            ai.state_data["last_repath_time"] = physics_time
                            ai.state_data["pursuit_repath"] = True
                            return Status.RUNNING

        if world.has_component(entity_id, MoveCommand):
            world.commands.remove_component(entity_id, MoveCommand)

        current_pos = pymunk.Vec2d(trans.x, trans.y)
        final_target = target_pos
        if ai.path:
            final_target = pymunk.Vec2d(*ai.path[-1])
        dist_to_final = (final_target - current_pos).length

        if dist_to_final < eff_accept_rad:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            ai.path = None
            NavigationController._cleanup_nav_state(ai)
            return Status.SUCCESS

        return Status.RUNNING
