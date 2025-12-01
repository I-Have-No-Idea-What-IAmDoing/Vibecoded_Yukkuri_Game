"""
Physics Utilities.
"""
from typing import Any, Tuple, Optional
import pymunk
from ..engine.ecs import World
from .components import PhysicsBody
from .systems.physics import PhysicsSystem

def add_physics_body(
    world: World,
    entity: int,
    shape_type: str,
    mass: float,
    position: Tuple[float, float],
    radius_or_size: Any,
    collision_category: int,
    collision_mask: int,
    elasticity: float = 0.5,
    friction: float = 0.5,
    set_userdata: bool = False
) -> None:
    """
    Adds a physics body to an entity.
    """
    physics_system = world.services.try_get(PhysicsSystem)
    if not physics_system:
        return

    # Check if entity already has physics
    if world.has_component(entity, PhysicsBody):
        return

    if shape_type == "circle":
        radius = float(radius_or_size)
        inertia = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, inertia)
        shape = pymunk.Circle(body, radius)
    elif shape_type == "box":
        width, height = radius_or_size
        inertia = pymunk.moment_for_box(mass, (width, height))
        body = pymunk.Body(mass, inertia)
        shape = pymunk.Poly.create_box(body, (width, height))
    else:
        raise ValueError(f"Unknown shape type: {shape_type}")

    body.position = position
    shape.elasticity = elasticity
    shape.friction = friction
    shape.filter = pymunk.ShapeFilter(categories=collision_category, mask=collision_mask)

    if set_userdata:
        body.userdata = entity

    physics_system.space.add(body, shape)
    world.add_component(entity, PhysicsBody(body=body, shape=shape))

def get_yukkuri_radius(growth_stage: str) -> float:
    """Returns the radius for a given growth stage."""
    if growth_stage == "Adult":
        return 20.0
    elif growth_stage == "Child":
        return 15.0
    else: # Baby
        return 10.0
