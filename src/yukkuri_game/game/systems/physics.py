"""
Module defining the PhysicsSystem logic.
"""

import pymunk
import math
from typing import Optional
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus, Event
from ...engine.events import EntityDestroyedEvent
from ..components import Transform, PhysicsBody


class PhysicsSystem(System):
    """
    System responsible for stepping the physics simulation and syncing with Transform components.

    Attributes:
        space (pymunk.Space): The pymunk physics space.
        accumulator (float): Time accumulator for fixed time step.
        time_step (float): The fixed time step for physics (default 1/60).
        max_frame_time (float): Maximum time to simulate per frame to avoid spiral of death.
    """

    def __init__(self, gravity: tuple[float, float] = (0, 0)):
        """
        Initializes the PhysicsSystem.

        Args:
            gravity (tuple[float, float]): The gravity vector (x, y). Defaults to (0, 0) for top-down.
        """
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 0.9  # Add damping to simulate friction/air resistance
        self.accumulator = 0.0
        self.time_step = 1.0 / 60.0
        self.max_frame_time = 0.25
        self.event_bus: Optional[EventBus] = None

    def on_entity_destroyed(self, event: Event) -> None:
        """
        Handles EntityDestroyedEvent to cleanup physics bodies.

        Args:
            event (Event): The event data.
        """
        if not isinstance(event, EntityDestroyedEvent):
            return

        # self.ecs_world is injected by World.add_system
        if getattr(self, "ecs_world", None):
            phys = self.ecs_world.get_component(event.entity_id, PhysicsBody)
            if phys:
                if phys.body in self.space.bodies:
                    self.space.remove(phys.body)
                if phys.shape in self.space.shapes:
                    self.space.remove(phys.shape)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the physics simulation.

        Steps the pymunk space and syncs PhysicsBody positions to Transform components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        if self.event_bus is None:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)

        # Clamp dt to avoid spiral of death with high time scales or lag
        if dt > self.max_frame_time:
            dt = self.max_frame_time

        self.accumulator += dt

        # Fixed timestep update loop
        # We process physics in fixed increments (self.time_step) to ensure determinism
        # and stability, regardless of the variable frame render time (dt).
        while self.accumulator >= self.time_step:
            self.space.step(self.time_step)
            self.accumulator -= self.time_step

        # Sync PhysicsBody -> Transform
        # Pymunk is the source of truth for position, so we update the ECS Transform component
        # to reflect the latest physics state for other systems (rendering, logic) to use.
        for entity, (phys, trans) in world.get_components_tuple(PhysicsBody, Transform):
            trans.prev_x = trans.x
            trans.prev_y = trans.y
            trans.prev_rotation = trans.rotation

            trans.x = phys.body.position.x
            trans.y = phys.body.position.y
            # Convert pymunk radians to degrees for pygame.
            # Pymunk's angle is in radians (positive is counter-clockwise).
            # Pygame's rotate function uses degrees (positive is counter-clockwise).
            # With a Y-down coordinate system, a counter-clockwise rotation in world space
            # appears as a clockwise rotation on screen. To achieve this with pygame's
            # CCW rotation, we must negate the angle.
            trans.rotation = -math.degrees(phys.body.angle)

    def clear(self) -> None:
        """
        Clears all bodies, shapes, and constraints from the physics space.
        """
        # Pymunk doesn't have a clear() method on space, so we remove everything.
        for shape in list(self.space.shapes):
            self.space.remove(shape)
        for body in list(self.space.bodies):
            self.space.remove(body)
        for constraint in list(self.space.constraints):
            self.space.remove(constraint)
