"""
Module defining the PhysicsSystem logic.
"""

import pymunk
from typing import Optional
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus, Event
from ...engine.events import EntityDestroyedEvent
from ..components import PhysicsBody, Transform


class PhysicsSystem(System):
    """
    System responsible for maintaining the Pymunk Space and syncing non-kinematic bodies.

    NOTE: The Physics Simulation Step is triggered by the KinematicMovementSystem
    inside its fixed update loop. This system only handles space management
    and syncing of DYNAMIC bodies (e.g. projectiles, debris) to the visual Transform.
    """

    def __init__(self, gravity: tuple[float, float] = (0, 0)):
        """
        Initializes the PhysicsSystem.

        Args:
            gravity (tuple[float, float]): The gravity vector (x, y). Defaults to (0, 0).
        """
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 0.9
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
        Updates the physics system state.
        1. Subscribes to events.
        2. Syncs DYNAMIC PhysicsBody positions to Transform components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.event_bus is None:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)

        # Sync PhysicsBody -> Transform for DYNAMIC bodies
        # Kinematic bodies are handled by KinematicMovementSystem.
        # Static bodies don't move (except if manually moved, but they are usually static).

        # Optimization: We could iterate all PhysicsBodies, but that's O(N).
        # Assuming most are Kinematic (Yukkuris), we only check Dynamic.

        for entity, (phys, trans) in world.get_components_tuple(PhysicsBody, Transform):
            if phys.body.body_type == pymunk.Body.DYNAMIC:
                trans.prev_x = trans.x
                trans.prev_y = trans.y
                trans.x = phys.body.position.x
                trans.y = phys.body.position.y
                # If we had rotation in transform:
                # trans.rotation = phys.body.angle

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
