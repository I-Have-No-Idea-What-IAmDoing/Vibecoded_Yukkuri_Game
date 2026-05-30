"""
Kinematic Movement System - Deterministic Character Controller.

Implements a robust Sweep-and-Slide algorithm for collision resolution,
providing deterministic movement suitable for networked games and replays.

Algorithm Overview:
1.  **Depenetration Pass**: Resolve any existing overlaps before movement.
2.  **Virtual Physics**: Integrate velocity based on input (acceleration/friction).
3.  **Sweep Pass**: Cast shape along movement vector to detect collisions.
4.  **Slide Resolution**: Project remaining velocity along collision surface.
5.  **Multi-Plane Handling**: Supports corner resolution (prevents V-corner sticking).

Performance Optimizations:
-   Stationary entities skip sweep logic entirely.
-   Polygon radius caching avoids repeated circumscribed circle calculations.
-   Fallback overlap check only triggers when sweep query misses edge cases.

Flight Integration:
-   Flying entities dynamically update collision filters based on altitude.
-   Ground units collide with LOW_OBSTACLE, flying units only with HIGH_OBSTACLE.
-   Swooping state enables ground unit collision for attack passes.

Fixed Timestep:
-   Movement runs via PhysicsFixedUpdateEvent for determinism.
-   Decoupled from render framerate for consistent physics behavior.
"""

import pymunk
from loguru import logger

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import PhysicsFixedUpdateEvent
from ..collision_constants import CollisionCategories
from ..components import (
    YukkuriStats,
)
from ...engine.components import (
    Flight,
    FlightState,
    MovementController,
    PhysicsBody,
    Transform,
)
from ..skill_service import SkillService
from ...engine.protocols import IPhysicsService


class KinematicMovementSystem(System):
    """
    Moves kinematic bodies using sweep-and-slide against world geometry.

    Features:
    -   Capsule/circle sweeping (no bounding box approximation).
    -   Multi-plane slide resolution for corners.
    -   Pre-step depenetration fallback.
    -   Composite shape support (stacked entities).

    Attributes:
        space (pymunk.Space | None): Physics space reference.
        skin_width (float): Collision skin width.
        event_bus (EventBus | None): EventBus reference.
        _kinematic_world (World | None): World reference for fixed updates.
        _poly_radius_cache (dict[pymunk.Poly, float]): Cache for polygon radii.
        skill_service (SkillService | None): SkillService reference.
    """

    def __init__(self) -> None:
        """Initializes the KinematicMovementSystem."""
        self.space: pymunk.Space | None = None
        self.event_bus: EventBus | None = None
        self._kinematic_world: World | None = None
        self.skill_service: SkillService | None = None

        # New Solver
        from ..physics.kinematic_solver import KinematicSolver

        self.solver = KinematicSolver()

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent) -> None:
        """
        Handles PhysicsFixedUpdateEvent to run deterministic physics.

        Args:
            event (PhysicsFixedUpdateEvent): The fixed update event.
        """
        if not self.space:
            return

        # Ensure solver has the space
        if self.solver.space != self.space:
            self.solver.set_space(self.space)

        if self._kinematic_world:
            self.fixed_update(self._kinematic_world, event.dt)
        else:
            logger.warning(
                "KinematicMovementSystem: Fixed update skipped because world is not initialized."
            )

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system, initializing services on first run.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.space:
            physics_system = world.services.try_get(IPhysicsService)
            if physics_system:
                self.space = physics_system.space
                self.solver.set_space(self.space)

        if not self.event_bus:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(PhysicsFixedUpdateEvent, self.on_fixed_update)
                self._kinematic_world = world

        self.skill_service = world.services.try_get(SkillService)
        self._kinematic_world = world

    def fixed_update(self, world: World, dt: float) -> None:
        """
        Runs the deterministic movement logic.

        Args:
            world (World): The ECS World.
            dt (float): Fixed delta time.
        """
        components = world.get_components_tuple(
            PhysicsBody, MovementController, Transform
        )

        # Lazy import to avoid circular dependency
        from ..skill_constants import SkillId

        for entity, (phys, controller, trans) in components:
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Sync Transform to Body
            start_pos = phys.body.position

            # Stationary entities skip sweep logic entirely.
            target_vel_sq = controller.target_velocity.length_squared
            current_vel_sq = controller.current_velocity.length_squared
            if target_vel_sq < 0.0001 and current_vel_sq < 0.0001:
                trans.prev_x = start_pos.x
                trans.prev_y = start_pos.y
                trans.x = start_pos.x
                trans.y = start_pos.y
                continue

            # Resolve any existing overlaps before movement using Solver.
            clean_pos = self.solver.resolve_penetration(phys, start_pos)
            if clean_pos != start_pos:
                phys.body.position = clean_pos
                start_pos = clean_pos

            trans.prev_x = start_pos.x
            trans.prev_y = start_pos.y

            # Flight Collision Filter Update
            flight = world.try_get_component(entity, Flight)
            if flight:
                self._update_flight_collision_filter(phys, flight)

            stats = world.try_get_component(entity, YukkuriStats)
            agility = stats.agility if stats else 1.0

            # Use Solver for movement
            dist_moved = self.move_and_slide(phys, controller, trans, dt, agility)

            # Award athletics XP based on distance traveled.
            if dist_moved > 0.1 and self.skill_service:
                self.skill_service.add_xp(entity, SkillId.ATHLETICS, dist_moved * 0.01)

            # Sync Transform back
            trans.x = phys.body.position.x
            trans.y = phys.body.position.y

    def move_and_slide(
        self,
        phys: PhysicsBody,
        controller: MovementController,
        trans: Transform,
        dt: float,
        agility: float = 1.0,
    ) -> float:
        """
        Wrapper for solver movement to allow mocking in tests.
        """
        if self.space and self.solver.space != self.space:
            self.solver.set_space(self.space)
        return self.solver.move_and_slide(phys, controller, trans, dt, agility)

    def resolve_penetration(self, phys: PhysicsBody, pos: pymunk.Vec2d) -> pymunk.Vec2d:
        """
        Wrapper for solver penetration resolution to allow tests to access it.
        """
        if self.space and self.solver.space != self.space:
            self.solver.set_space(self.space)
        return self.solver.resolve_penetration(phys, pos)

    def _update_flight_collision_filter(
        self, phys: PhysicsBody, flight: Flight
    ) -> None:
        """
        Updates the collision filter on all shapes of the physics body based on flight state.

        - GROUNDED/LANDING/TAKEOFF (low altitude): Collide with ground units, low obstacles, high obstacles, water.
        - FLYING/HOVERING (high altitude): Only collide with flying units and high obstacles.
        - SWOOPING (attack descent): Collide with ground units, low obstacles, high obstacles.

        Args:
            phys (PhysicsBody): The entity's physics body.
            flight (Flight): The flight component.
        """
        CC = CollisionCategories

        if flight.state in (FlightState.FLYING, FlightState.HOVERING):
            # High altitude: ignore ground units and low obstacles
            new_categories = CC.FLYING_UNIT
            new_mask = CC.FLYING_UNIT | CC.HIGH_OBSTACLE
        elif flight.state == FlightState.SWOOPING:
            # Swooping: can hit ground units but still ignores low obstacles for attack
            new_categories = CC.FLYING_UNIT
            new_mask = (
                CC.GROUND_UNIT | CC.FLYING_UNIT | CC.HIGH_OBSTACLE | CC.LOW_OBSTACLE
            )
        else:
            # GROUNDED, LANDING, TAKEOFF, FALLING: normal ground collision
            new_categories = CC.GROUND_UNIT
            new_mask = (
                CC.GROUND_UNIT | CC.LOW_OBSTACLE | CC.HIGH_OBSTACLE | CC.WATER | CC.ITEM
            )

        for shape in phys.body.shapes:
            if shape.sensor:
                continue
            # Preserve the group (for self-collision avoidance if used)
            current_filter = shape.filter
            shape.filter = pymunk.ShapeFilter(
                group=current_filter.group,
                categories=new_categories,
                mask=new_mask,
            )
