"""
Physics System - Pymunk Integration and Fixed Timestep Simulation.

Wraps Pymunk physics engine for deterministic collision and movement.
Uses a fixed timestep accumulator pattern for frame-rate independent physics.

Fixed Timestep Pattern:
1. Accumulate render delta time into an accumulator
2. While accumulator >= timestep: step physics, broadcast event, decrement
3. Remaining accumulator < timestep becomes interpolation alpha for rendering

Spatial Hash Optimization:
- Pre-configured for ~50px entity diameter (typical Yukkuri size)
- 2000 bucket count for good distribution with many entities

Coordinate System:
- Pymunk uses radians (CCW positive) for rotation
- Pygame uses degrees (CCW positive)
- Y-down screen means CCW world = CW visual, so we negate angle

Event Integration:
- Broadcasts PhysicsFixedUpdateEvent each physics step
- Subscribes to EntityDestroyedEvent for cleanup
- Subscribes to WorldClearedEvent for full reset
"""

import pymunk
import math
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus, Event
from ...engine.events import (
    EntityDestroyedEvent,
    PhysicsFixedUpdateEvent,
    WorldClearedEvent,
)
from ..components import Transform, PhysicsBody


class PhysicsSystem(System):
    """
    Steps Pymunk simulation and syncs bodies to Transform components.

    Pymunk is source of truth for entity positions. After each step,
    body positions are copied to Transform for rendering and game logic.
    """

    # Default physics timestep (60 FPS equivalent)
    DEFAULT_TIMESTEP = 1.0 / 60.0

    # Maximum frame time to prevent spiral of death during lag spikes
    MAX_FRAME_TIME = 0.25

    def __init__(self, gravity: tuple[float, float] = (0, 0)):
        """
        Initializes the PhysicsSystem.

        Args:
            gravity: Gravity vector (x, y). Default (0, 0) for top-down games.
        """
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 0.9  # Friction/air resistance simulation

        # Spatial hash for O(1) collision broadphase
        # dim=50: Average Yukkuri diameter, count=2000: Expected entity count * 4
        self.space.use_spatial_hash(dim=50.0, count=2000)

        self.accumulator = 0.0
        self.time_step = self.DEFAULT_TIMESTEP
        self.max_frame_time = self.MAX_FRAME_TIME
        self.event_bus: EventBus | None = None

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

    def on_world_cleared(self, event: Event) -> None:
        """
        Handles WorldClearedEvent to cleanup all physics bodies.

        Args:
            event (Event): The event data.
        """
        self.clear()

    def initialize(self) -> None:
        """
        Initializes the system by subscribing to events.
        """
        self.event_bus = self.ecs_world.services.try_get(EventBus)
        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

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
                self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

        # Clamp dt to avoid spiral of death with high time scales or lag
        if dt > self.max_frame_time:
            dt = self.max_frame_time

        self.accumulator += dt

        # Fixed timestep update loop for determinism.
        while self.accumulator >= self.time_step:
            if self.event_bus:
                self.event_bus.publish(PhysicsFixedUpdateEvent(dt=self.time_step))

            self.space.step(self.time_step)
            self.accumulator -= self.time_step

        # Sync PhysicsBody -> Transform.
        for entity, (phys, trans) in world.get_components_tuple(PhysicsBody, Transform):
            trans.prev_x = trans.x
            trans.prev_y = trans.y
            trans.prev_rotation = trans.rotation

            trans.x = phys.body.position.x
            trans.y = phys.body.position.y
            # Convert pymunk radians to pygame degrees (negate for Y-down screen).
            trans.rotation = -math.degrees(phys.body.angle)

    def clear(self) -> None:
        """
        Clears all bodies, shapes, and constraints from the physics space.
        """
        for shape in list(self.space.shapes):
            self.space.remove(shape)
        for body in list(self.space.bodies):
            self.space.remove(body)
        for constraint in list(self.space.constraints):
            self.space.remove(constraint)
