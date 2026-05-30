"""
Physics System - Pymunk Integration and Fixed Timestep Simulation.
"""

import math
import pymunk

from ..ecs import System, World
from ..event_bus import Event, EventBus
from ..events import (
    EntityDestroyedEvent,
    PhysicsFixedUpdateEvent,
    WorldClearedEvent,
)
from ...engine.components import PhysicsBody, Transform
from ...engine.systems.time import TimeSystem


class PhysicsSystem(System):
    run_after = [TimeSystem]

    """
    Steps Pymunk simulation and syncs bodies to Transform components.
    """

    DEFAULT_TIMESTEP = 1.0 / 60.0
    MAX_FRAME_TIME = 0.25

    def __init__(self, gravity: tuple[float, float] = (0, 0)):
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 0.9
        self.space.use_spatial_hash(dim=50.0, count=2000)
        self.space.sleep_time_threshold = 0.5
        self.accumulator = 0.0
        self.time_step = self.DEFAULT_TIMESTEP
        self.max_frame_time = self.MAX_FRAME_TIME
        self.event_bus: EventBus | None = None

    def on_entity_destroyed(self, event: Event) -> None:
        if not isinstance(event, EntityDestroyedEvent):
            return
        if getattr(self, "ecs_world", None):
            phys = self.ecs_world.try_get_component(event.entity_id, PhysicsBody)
            if phys:
                if phys.body in self.space.bodies:
                    self.space.remove(phys.body)
                for shape in list(phys.body.shapes):
                    if shape in self.space.shapes:
                        self.space.remove(shape)

    def on_world_cleared(self, event: Event) -> None:
        self.clear()

    def initialize(self) -> None:
        self.event_bus = self.ecs_world.services.try_get(EventBus)
        if self.event_bus:
            self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
            self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

    def update(self, world: World, dt: float) -> None:
        if self.event_bus is None:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
                self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

        if dt > self.max_frame_time:
            dt = self.max_frame_time

        self.accumulator += dt

        # Check if we will step
        will_step = self.accumulator >= self.time_step

        if will_step:
            # Capture the pre-simulation state ONCE for all physical entities
            for entity, (phys, trans) in world.get_components_tuple(
                PhysicsBody, Transform
            ):
                trans.prev_x = trans.x
                trans.prev_y = trans.y
                trans.prev_rotation = trans.rotation

        # Run fixed simulation steps
        while self.accumulator >= self.time_step:
            if self.event_bus:
                self.event_bus.publish(
                    PhysicsFixedUpdateEvent(dt=self.time_step)
                )
            self.space.step(self.time_step)
            self.accumulator -= self.time_step

        if will_step:
            # Sync the new physics body state to Transform
            for entity, (phys, trans) in world.get_components_tuple(
                PhysicsBody, Transform
            ):
                if phys.body.is_sleeping:
                    # If already sleeping and didn't move, keep alignment
                    if (
                        phys.body.position.x == trans.x
                        and phys.body.position.y == trans.y
                    ):
                        trans.prev_x = trans.x
                        trans.prev_y = trans.y
                        trans.prev_rotation = trans.rotation
                        continue

                trans.x = phys.body.position.x
                trans.y = phys.body.position.y
                trans.rotation = -math.degrees(phys.body.angle)

    def clear(self) -> None:
        for shape in list(self.space.shapes):
            self.space.remove(shape)
        for body in list(self.space.bodies):
            self.space.remove(body)
        for constraint in list(self.space.constraints):
            self.space.remove(constraint)
