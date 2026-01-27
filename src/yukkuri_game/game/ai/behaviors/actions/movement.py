import math
from typing import TYPE_CHECKING, Any, cast

import pymunk
from py_trees.common import Status

from yukkuri_game.engine import rng

from ...base_action import Action
from ....components import (
    Transform,
    PhysicsBody,
    MovementController,
    MoveCommand,
)
from ....yukkuri_components import (
    AIState,
    Needs,
    Flight,
    FlightState,
    Predator,
)
from ...navigation_service import NavigationService
from ...navigation_constants import TraversalCapability
from yukkuri_game.engine.types import EntityID

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World

WAYPOINT_ACCEPTANCE_RADIUS = 20.0
LOW_ENERGY_THRESHOLD = 30.0


class MoveToTarget(Action):
    """
    Moves the entity towards a target using direct velocity control.

    Attributes:
        speed (float): Movement speed.
        acceptance_radius (float): Distance to consider target reached.
    """

    def __init__(
        self,
        name: str = "Move To Target",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
        speed: float = 100.0,
        acceptance_radius: float = 40.0,
    ):
        """
        Initializes the MoveToTarget action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
            speed (float): Movement speed.
            acceptance_radius (float): Distance threshold.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed
        self.acceptance_radius = acceptance_radius

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)
        needs = self.world.get_component(self.entity_id, Needs)
        controller = self.world.get_component(self.entity_id, MovementController)

        if ai is None or trans is None or needs is None or controller is None:
            return Status.FAILURE

        # Determine Target Position
        target_pos = None
        if ai.current_target_id != -1:
            target_trans = self.world.get_component(ai.current_target_id, Transform)
            if target_trans:
                target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
            else:
                ai.current_target_id = cast(EntityID, -1)
                controller.target_velocity = pymunk.Vec2d(0, 0)
                if self.world.has_component(self.entity_id, MoveCommand):
                    self.world.remove_component(self.entity_id, MoveCommand)
                return Status.FAILURE
        elif (
            ai.state_data
            and "target_x" in ai.state_data
            and "target_y" in ai.state_data
        ):
            target_pos = pymunk.Vec2d(
                ai.state_data["target_x"], ai.state_data["target_y"]
            )

        if target_pos is None:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            if self.world.has_component(self.entity_id, MoveCommand):
                self.world.remove_component(self.entity_id, MoveCommand)
            return Status.FAILURE

        current_pos = pymunk.Vec2d(trans.x, trans.y)

        # Close-Range / Line-of-Sight Optimization
        is_visible = ai.current_target_id == -1 or (
            ai.current_target_id in ai.visible_entities
        )

        if is_visible and target_pos:
            dist_to_target = (target_pos - current_pos).length
            use_direct_steering = False

            if dist_to_target < 150.0:
                use_direct_steering = True
            elif dist_to_target < 400.0:
                from ....systems.physics import PhysicsSystem

                physics_sys = self.world.services.try_get(PhysicsSystem)
                if physics_sys and hasattr(physics_sys, "space"):
                    space = physics_sys.space
                    filter_ = pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS())
                    hit = space.segment_query_first(
                        current_pos, target_pos, 1.0, filter_
                    )
                    if hit is None:
                        use_direct_steering = True
                    elif hit.shape:
                        if ai.current_target_id != -1:
                            target_phys = self.world.try_get_component(
                                ai.current_target_id, PhysicsBody
                            )
                            if target_phys and hit.shape.body == target_phys.body:
                                use_direct_steering = True

            if use_direct_steering:
                if dist_to_target < self.acceptance_radius:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    ai.path = None
                    if self.world.has_component(self.entity_id, MoveCommand):
                        self.world.remove_component(self.entity_id, MoveCommand)
                    return Status.SUCCESS

                speed_modifier = 1.0
                if needs.energy < 30:
                    speed_modifier = 0.5

                self.world.add_component(
                    self.entity_id,
                    MoveCommand(
                        target_pos=target_pos,
                        target_entity_id=(
                            ai.current_target_id if ai.current_target_id != -1 else None
                        ),
                        speed_multiplier=speed_modifier,
                        priority=2,
                    ),
                )

                if ai.path:
                    ai.path = None
                return Status.RUNNING

        if target_pos:
            dist_sq = (target_pos - current_pos).length_squared
            if dist_sq < self.acceptance_radius * self.acceptance_radius:
                controller.target_velocity = pymunk.Vec2d(0, 0)
                ai.path = None
                if self.world.has_component(self.entity_id, MoveCommand):
                    self.world.remove_component(self.entity_id, MoveCommand)
                return Status.SUCCESS

        # Pathfinding (Async)
        if ai.path is None:
            state_data = ai.state_data if ai.state_data else {}
            is_requesting = state_data.get("path_requesting", False)
            path_failed = state_data.get("path_failed", False)

            if is_requesting:
                now = self.world.time
                request_timestamp = state_data.get("path_request_time", 0.0)
                if (now - request_timestamp) > 2.0:
                    state_data["path_requesting"] = False
                elif path_failed:
                    state_data["path_requesting"] = False
                    if "path_failed" in state_data:
                        del state_data["path_failed"]
                    ai.state_data = state_data
                else:
                    return Status.RUNNING
            elif not path_failed:
                nav_service = self.world.services.try_get(NavigationService)
                if nav_service:
                    capabilities = TraversalCapability.WALK
                    flight_comp = self.world.try_get_component(self.entity_id, Flight)
                    if flight_comp and flight_comp.stamina > 20:
                        capabilities |= TraversalCapability.FLY
                        if flight_comp.state == FlightState.GROUNDED:
                            flight_comp.state = FlightState.TAKEOFF

                    priority = 2
                    if ai.state_data and ai.state_data.get("pursuit_repath", False):
                        priority = 0
                        ai.state_data["pursuit_repath"] = False

                    nav_service.request_path(
                        self.entity_id,
                        (trans.x, trans.y),
                        (target_pos.x, target_pos.y),
                        capabilities=capabilities,
                        priority=priority,
                        timestamp=self.world.time,
                    )

                    if ai.state_data is None:
                        ai.state_data = {}
                    ai.state_data["path_requesting"] = True
                    ai.state_data["path_request_time"] = self.world.time
                    ai.state_data["path_destination"] = (target_pos.x, target_pos.y)
                    if "path_failed" in ai.state_data:
                        del ai.state_data["path_failed"]

                    return Status.RUNNING

        # Drift Detection
        if ai.path and target_pos:
            is_visible = ai.current_target_id == -1 or (
                ai.current_target_id in ai.visible_entities
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
                    if ai.current_target_id != -1:
                        target_phys = self.world.try_get_component(
                            ai.current_target_id, PhysicsBody
                        )
                    if target_phys and target_phys.body:
                        t_speed = target_phys.body.velocity.length
                        val = max(20.0, 50.0 - (t_speed * 0.3))
                        drift_threshold_sq = val * val

                    drift_sq = (target_pos - pymunk.Vec2d(*path_dest)).length_squared
                    if drift_sq > drift_threshold_sq:
                        now = self.world.time
                        last_repath_time = ai.state_data.get("last_repath_time", 0.0)
                        if now - last_repath_time > 0.5:
                            ai.path = None
                            ai.state_data["last_repath_time"] = now
                            ai.state_data["pursuit_repath"] = True
                            return Status.RUNNING

            if ai.path is None:
                if ai.state_data and ai.state_data.get("path_requesting"):
                    ai.state_data["path_requesting"] = False

                vector_to_target = target_pos - pymunk.Vec2d(trans.x, trans.y)
                dist = vector_to_target.length

                if dist < self.acceptance_radius:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    if self.world.has_component(self.entity_id, MoveCommand):
                        self.world.remove_component(self.entity_id, MoveCommand)
                    return Status.SUCCESS

                speed_modifier = 1.0
                if needs.energy < 30:
                    speed_modifier = 0.5

                self.world.add_component(
                    self.entity_id,
                    MoveCommand(
                        target_pos=target_pos,
                        target_entity_id=(
                            ai.current_target_id if ai.current_target_id != -1 else None
                        ),
                        speed_multiplier=speed_modifier,
                        priority=2,
                    ),
                )
                return Status.RUNNING

        # Path Following Logic
        if ai.path:
            # Get next waypoint
            next_point = pymunk.Vec2d(*ai.path[0])
            dist_to_waypoint = (next_point - current_pos).length

            # Waypoint reached?
            if dist_to_waypoint < WAYPOINT_ACCEPTANCE_RADIUS:
                ai.path.pop(0)
                if not ai.path:
                    # Path finished
                    pass
                else:
                    next_point = pymunk.Vec2d(*ai.path[0])

            if ai.path:
                speed_modifier = 1.0
                if needs.energy < LOW_ENERGY_THRESHOLD:
                    speed_modifier = 0.5

                self.world.add_component(
                    self.entity_id,
                    MoveCommand(
                        target_pos=next_point,
                        target_entity_id=None,
                        speed_multiplier=speed_modifier,
                        priority=2,
                    ),
                )
                return Status.RUNNING

        if self.world.has_component(self.entity_id, MoveCommand):
            self.world.remove_component(self.entity_id, MoveCommand)

        current_pos = pymunk.Vec2d(trans.x, trans.y)
        dist_to_final = (target_pos - current_pos).length

        if dist_to_final < self.acceptance_radius:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            ai.path = []
            return Status.SUCCESS

        return Status.RUNNING


class Wander(Action):
    """
    Causes the entity to wander to a random location.

    Attributes:
        width (int): Wander area width.
        height (int): Wander area height.
        move_action (MoveToTarget | None): Sub-action for movement.
    """

    def __init__(
        self,
        name: str = "Wander",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
        width: int = 3000,
        height: int = 3000,
    ):
        """
        Initializes the Wander action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
            width (int): Wander area width.
            height (int): Wander area height.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.width = width
        self.height = height
        self.move_action: MoveToTarget | None = None

    def initialise(self) -> None:
        if self.world is None or self.entity_id is None:
            return

        ai = self.world.get_component(self.entity_id, AIState)
        if ai:
            tx = rng.uniform(0, self.width)
            ty = rng.uniform(0, self.height)
            ai.state_data = {"target_x": tx, "target_y": ty}
            ai.path = None
            ai.current_target_id = EntityID(-1)

        self.move_action = MoveToTarget(
            entity_id=self.entity_id, world=self.world, blackboard=self.blackboard
        )

    def update(self) -> Status:
        if self.move_action:
            return self.move_action.update()
        return Status.FAILURE


class Swoop(Action):
    """
    Rapid descent to attack target.
    """

    def __init__(
        self,
        name: str = "Swoop",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the Swoop action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        flight = self.world.try_get_component(self.entity_id, Flight)
        if not flight:
            return Status.FAILURE

        if flight.state != FlightState.SWOOPING:
            flight.state = FlightState.SWOOPING
            flight.vertical_speed = 50.0

        if flight.altitude <= 5.0:
            flight.state = FlightState.GROUNDED
            flight.altitude = 0.0
            return Status.SUCCESS

        return Status.RUNNING


class FleePredator(Action):
    """
    Action to flee from nearby predators.

    Attributes:
        speed (float): Flee speed.
    """

    def __init__(
        self,
        name: str = "Flee Predator",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
        speed: float = 150.0,
    ):
        """
        Initializes the FleePredator action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
            speed (float): Flee speed.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        my_trans = self.world.get_component(self.entity_id, Transform)
        controller = self.world.get_component(self.entity_id, MovementController)
        if not my_trans or not controller:
            return Status.FAILURE

        min_dist = float("inf")
        flee_start_dist = 200.0
        nearest_predator = None

        for uid, (pred, trans) in self.world.get_components_tuple(Predator, Transform):
            if uid == self.entity_id:
                continue

            dist = math.hypot(trans.x - my_trans.x, trans.y - my_trans.y)
            if dist < flee_start_dist and dist < min_dist:
                min_dist = dist
                nearest_predator = trans

        if nearest_predator:
            flee_vec = pymunk.Vec2d(
                my_trans.x - nearest_predator.x, my_trans.y - nearest_predator.y
            )
            if flee_vec.length > 0:
                flee_vec = flee_vec.normalized() * self.speed
                controller.target_velocity = flee_vec
                return Status.RUNNING

        return Status.FAILURE


class FleeFromTarget(Action):
    """
    Calculates a destination AWAY from the current target.

    Attributes:
        flee_dist (float): Distance to flee.
    """

    def __init__(
        self,
        name: str = "Run Away",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
        dist: float = 300.0,
    ):
        """
        Initializes the FleeFromTarget action.

        Args:
            name (str): Behavior name.
            entity_id (int | None): Entity ID.
            world (World | None): ECS World.
            blackboard (Any | None): Blackboard.
            dist (float): Distance to flee.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.flee_dist = dist

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        target_id = ai.current_target_id
        if target_id == -1:
            return Status.FAILURE

        target_trans = self.world.try_get_component(target_id, Transform)
        if not target_trans:
            return Status.FAILURE

        dx = target_trans.x - trans.x
        dy = target_trans.y - trans.y
        dist = math.hypot(dx, dy)

        if dist < 0.001:
            dx = 1.0
            dy = 0.0
            dist = 1.0

        dx /= dist
        dy /= dist

        run_x = trans.x - (dx * self.flee_dist)
        run_y = trans.y - (dy * self.flee_dist)

        ai.state_data = {"target_x": run_x, "target_y": run_y}
        ai.path = None
        ai.current_target_id = cast(EntityID, -1)

        return Status.SUCCESS
