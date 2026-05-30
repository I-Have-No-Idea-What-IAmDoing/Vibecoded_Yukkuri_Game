"""
Movement Actions for Behavior Trees.

This module defines Behavior Tree action nodes related to entity movement,
such as moving to a target, wandering, fleeing, and swooping.
"""

import math
from typing import TYPE_CHECKING, Any, cast

import pymunk
from py_trees.common import Status

from .....engine import rng
from .....engine.types import EntityID

from ....components import (
    AIState,
    MoveCommand,
    Needs,
    Predator,
    YukkuriStats,
)
from .....engine.components import (
    Flight,
    FlightState,
    MovementController,
    Transform,
)
from ...base_action import Action
from ...navigation_controller import NavigationController


if TYPE_CHECKING:
    from .....engine.ecs import World

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
        """
        Updates the movement logic.

        Returns:
            Status: The execution status (RUNNING, SUCCESS, FAILURE).
        """
        super().update()
        if self.world is None or self.entity_id is None:
            from loguru import logger
            logger.error("MoveToTarget: world or entity_id is None")
            return Status.FAILURE

        ai = self.world.try_get_component(self.entity_id, AIState)
        trans = self.world.try_get_component(self.entity_id, Transform)
        needs = self.world.try_get_component(self.entity_id, Needs)
        controller = self.world.try_get_component(
            self.entity_id, MovementController
        )

        if ai is None or trans is None or needs is None or controller is None:
            from loguru import logger
            logger.error(
                f"MoveToTarget: Missing component for entity {self.entity_id}: "
                f"ai={ai is not None}, trans={trans is not None}, "
                f"needs={needs is not None}, controller={controller is not None}"
            )
            return Status.FAILURE

        # Determine Target Position
        target_pos = None
        if ai.current_target_id != -1:
            if (
                ai.current_target_id in ai.failed_targets
                and not ai.manual_override
            ):
                controller.target_velocity = pymunk.Vec2d(0, 0)
                if self.world.has_component(self.entity_id, MoveCommand):
                    self.world.commands.remove_component(
                        self.entity_id, MoveCommand
                    )
                return Status.FAILURE

            target_trans = self.world.try_get_component(
                ai.current_target_id, Transform
            )
            if target_trans:
                target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
            else:
                ai.current_target_id = cast(EntityID, -1)
                controller.target_velocity = pymunk.Vec2d(0, 0)
                if self.world.has_component(self.entity_id, MoveCommand):
                    self.world.commands.remove_component(
                        self.entity_id, MoveCommand
                    )
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
            from loguru import logger
            logger.error(
                f"MoveToTarget: target_pos is None for entity {self.entity_id}! "
                f"current_target_id={ai.current_target_id}, "
                f"state_data={ai.state_data}"
            )
            controller.target_velocity = pymunk.Vec2d(0, 0)
            if self.world.has_component(self.entity_id, MoveCommand):
                self.world.commands.remove_component(
                    self.entity_id, MoveCommand
                )
            return Status.FAILURE

        from ...commands import CommandType

        self.publish_command(
            CommandType.MOVE_TO,
            {
                "target_x": target_pos.x,
                "target_y": target_pos.y,
                "target_entity_id": (
                    ai.current_target_id if ai.current_target_id != -1 else None
                ),
                "acceptance_radius": self.acceptance_radius,
            },
        )

        return NavigationController.navigate_to(
            world=self.world,
            entity_id=self.entity_id,
            target_pos=target_pos,
            target_entity_id=(
                ai.current_target_id if ai.current_target_id != -1 else None
            ),
            speed=self.speed,
            acceptance_radius=self.acceptance_radius,
        )

    def on_cleanup(self) -> None:
        """
        Cleans up movement commands, velocities, and transient path request flags.
        """
        if self.world is None or self.entity_id is None:
            return

        controller = self.world.try_get_component(
            self.entity_id, MovementController
        )
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)

        if self.world.has_component(self.entity_id, MoveCommand):
            self.world.commands.remove_component(self.entity_id, MoveCommand)

        ai = self.world.try_get_component(self.entity_id, AIState)
        if ai:
            ai.path = None
            if ai.state_data:
                ai.state_data.pop("path_requesting", None)
                ai.state_data.pop("path_destination", None)
                ai.state_data.pop("pursuit_repath", None)
                ai.state_data.pop("target_x", None)
                ai.state_data.pop("target_y", None)
                ai.state_data.pop("stuck_count", None)



class Wander(Action):
    """
    Causes the entity to wander to a random location.

    Attributes:
        width (int): Wander area width.
        height (int): Wander area height.
        acceptance_radius (float): Distance to consider target reached.
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
        acceptance_radius: float = 35.0,
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
            acceptance_radius (float): Distance to consider target reached.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.width = width
        self.height = height
        self.acceptance_radius = acceptance_radius
        self.move_action: MoveToTarget | None = None

    def initialise(self) -> None:
        """Initializes the wander target."""
        if self.world is None or self.entity_id is None:
            return

        from .....config import GameConfig
        config = self.world.services.try_get(GameConfig)
        default_w = float(config.world.width) if config else 3000.0
        default_h = float(config.world.height) if config else 3000.0

        w = (
            float(self.width)
            if (self.width is not None and self.width > 0)
            else default_w
        )
        h = (
            float(self.height)
            if (self.height is not None and self.height > 0)
            else default_h
        )

        # Robust defensive bounds safety fallback
        if w < 100.0:
            w = 3000.0
        if h < 100.0:
            h = 3000.0

        ai = self.world.try_get_component(self.entity_id, AIState)
        trans = self.world.try_get_component(self.entity_id, Transform)

        if ai:
            from .....game.ai.navigation_constants import (
                TraversalCapability,
            )
            from .....game.ai.navigation_service import (
                NavigationService,
            )

            nav_service = self.world.services.try_get(NavigationService)

            tx, ty = 0.0, 0.0
            found_target = False

            # Try up to 20 times to find a walkable wander target cell
            for _ in range(20):
                cand_x = rng.uniform(0.0, w)
                cand_y = rng.uniform(0.0, h)

                # Ensure generated target is at a safe minimum distance
                if trans:
                    curr_pos = pymunk.Vec2d(trans.x, trans.y)
                    target_pos = pymunk.Vec2d(cand_x, cand_y)
                    min_dist = self.acceptance_radius + 50.0
                    if (target_pos - curr_pos).length < min_dist:
                        # Jitter/shift the target away in a random direction
                        angle = rng.uniform(0.0, 2.0 * math.pi)
                        shift_dir = pymunk.Vec2d(
                            math.cos(angle), math.sin(angle)
                        )
                        shift_dist = min_dist + rng.uniform(10.0, 50.0)
                        new_pos = curr_pos + shift_dir * shift_dist
                        # Clamp to world bounds
                        cand_x = max(0.0, min(new_pos.x, w))
                        cand_y = max(0.0, min(new_pos.y, h))

                if nav_service:
                    gx = int(round(cand_x / nav_service.grid_step_size))
                    gy = int(round(cand_y / nav_service.grid_step_size))
                    gx = max(0, min(gx, nav_service.grid.width - 1))
                    gy = max(0, min(gy, nav_service.grid.height - 1))

                    if nav_service.grid.is_walkable(
                        gx, gy, TraversalCapability.WALK
                    ):
                        tx, ty = cand_x, cand_y
                        found_target = True
                        break
                else:
                    tx, ty = cand_x, cand_y
                    found_target = True
                    break

            if not found_target:
                # Fallback if no walkable cell found in 20 attempts
                tx = rng.uniform(0.0, w)
                ty = rng.uniform(0.0, h)

            ai.state_data = {"target_x": tx, "target_y": ty}
            ai.path = None
            ai.current_target_id = EntityID(-1)

        self.move_action = MoveToTarget(
            entity_id=self.entity_id,
            world=self.world,
            blackboard=self.blackboard,
            acceptance_radius=self.acceptance_radius,
        )

    def update(self) -> Status:
        """
        Updates the wander logic by delegating to MoveToTarget.

        Returns:
            Status: The execution status.
        """
        if self.move_action:
            for _ in self.move_action.tick():
                pass
            return self.move_action.status
        return Status.FAILURE

    def on_cleanup(self) -> None:
        """Cleans up the delegated movement action and its movement states."""
        if self.move_action:
            self.move_action.on_cleanup()
        if self.world is None:
            return
        ai = self.world.try_get_component(self.entity_id, AIState)
        if ai and ai.state_data:
            ai.state_data.pop("target_x", None)
            ai.state_data.pop("target_y", None)


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
        """
        Updates the swoop logic.

        Returns:
            Status: The execution status.
        """
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
        """
        Updates the flee logic.

        Returns:
            Status: The execution status.
        """
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        my_trans = self.world.try_get_component(self.entity_id, Transform)
        controller = self.world.try_get_component(self.entity_id, MovementController)
        if not my_trans or not controller:
            return Status.FAILURE

        my_stats = self.world.try_get_component(self.entity_id, YukkuriStats)
        my_type_id = my_stats.type_id if my_stats else None

        min_dist = float("inf")
        flee_start_dist = 200.0
        nearest_predator = None

        for uid, (pred, trans) in self.world.get_components_tuple(Predator, Transform):
            if uid == self.entity_id:
                continue

            # Only flee predators that actually hunt this entity's type.
            is_hostile = (
                "Yukkuri" in pred.prey_tags
                or (my_type_id is not None and my_type_id in pred.prey_tags)
            )
            if not is_hostile:
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

                from ...commands import CommandType

                published = self.publish_command(
                    CommandType.FLEE,
                    {
                        "velocity_x": flee_vec.x,
                        "velocity_y": flee_vec.y,
                    },
                )
                if not published:
                    controller.target_velocity = flee_vec

                ai = self.world.try_get_component(self.entity_id, AIState)
                if ai:
                    ai.path = None

                return Status.RUNNING

        return Status.FAILURE

    def on_cleanup(self) -> None:
        """
        Cleans up locomotion velocities when fleeing predator ends.
        """
        if self.world is None or self.entity_id is None:
            return

        controller = self.world.try_get_component(
            self.entity_id, MovementController
        )
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)



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
        """
        Updates the flee target logic.

        Returns:
            Status: The execution status.
        """
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.try_get_component(self.entity_id, AIState)
        trans = self.world.try_get_component(self.entity_id, Transform)

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

        # Base flee direction (directly away from threat)
        flee_dir = -pymunk.Vec2d(dx, dy)

        # Try a few angles: 0, +15, -15, +30, -30, +45, -45 degrees (in radians)
        angles_to_try = [0.0, 0.26, -0.26, 0.52, -0.52, 0.78, -0.78]

        from .....config import GameConfig
        config = self.world.services.try_get(GameConfig)
        w = float(config.world.width) if config else 3000.0
        h = float(config.world.height) if config else 3000.0

        from .....game.ai.navigation_constants import (
            TraversalCapability,
            )
        from .....game.ai.navigation_service import NavigationService

        nav_service = self.world.services.try_get(NavigationService)

        run_x = trans.x + flee_dir.x * self.flee_dist
        run_y = trans.y + flee_dir.y * self.flee_dist
        run_x = max(0.0, min(run_x, w))
        run_y = max(0.0, min(run_y, h))

        for angle in angles_to_try:
            cand_dir = flee_dir.rotated(angle)
            candidate_x = trans.x + cand_dir.x * self.flee_dist
            candidate_y = trans.y + cand_dir.y * self.flee_dist

            candidate_x = max(0.0, min(candidate_x, w))
            candidate_y = max(0.0, min(candidate_y, h))

            if nav_service:
                gx = int(round(candidate_x / nav_service.grid_step_size))
                gy = int(round(candidate_y / nav_service.grid_step_size))
                gx = max(0, min(gx, nav_service.grid.width - 1))
                gy = max(0, min(gy, nav_service.grid.height - 1))

                if nav_service.grid.is_walkable(
                    gx, gy, TraversalCapability.WALK
                ):
                    run_x, run_y = candidate_x, candidate_y
                    break
            else:
                run_x, run_y = candidate_x, candidate_y
                break

        ai.state_data = {"target_x": run_x, "target_y": run_y}
        ai.path = None
        ai.current_target_id = cast(EntityID, -1)

        return Status.SUCCESS

    def on_cleanup(self) -> None:
        """
        Cleans up resources when FleeFromTarget finishes or is aborted.
        """
        pass
