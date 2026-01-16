"""
Prefab for Item entities.
"""

from typing import Any
import pymunk
from ...engine.ecs import World
from ...engine.resource_manager import ResourceManager
from ..components import (
    Transform,
    Sprite,
    Selectable,
    VisualTransform,
    PhysicsBody,
    LightSource,
    Occluder,
    FlickerStyle,
)
from ..yukkuri_components import ItemStats, Poop
from ..components_persistence import StableIDComponent, Persistable
from ..collision_constants import CollisionCategories
from ..systems.physics import PhysicsSystem
from ..ai.navigation_service import NavigationService, ObstacleType


def create_item(world: World, type_id: str, x: float, y: float) -> int:
    """
    Creates an Item entity.

    Args:
        world (World): The ECS World.
        type_id (str): The item type identifier.
        x (float): World x-coordinate.
        y (float): World y-coordinate.

    Returns:
        int: The created entity ID.

    Raises:
        ValueError: If the item type is unknown.
    """
    rm = world.services.get(ResourceManager)
    physics_system = world.services.try_get(PhysicsSystem)

    data = rm.item_types.get(type_id)
    if not data:
        raise ValueError(f"Unknown item type: {type_id}")

    entity = world.create_entity()
    world.add_component(entity, Transform(x=x, y=y))

    def _get_attr(d: Any, k: str, default: Any = None) -> Any:
        if isinstance(d, dict):
            return d.get(k, default)
        return getattr(d, k, default)

    image = _get_attr(data, "image", "item_default.png")
    width = _get_attr(data, "width", 32)
    height = _get_attr(data, "height", 32)
    frame_count = _get_attr(data, "frame_count", 1)
    frame_duration = _get_attr(data, "frame_duration", 0.1)
    loop = _get_attr(data, "loop", True)

    world.add_component(
        entity,
        Sprite(
            image_name=image,
            width=width,
            height=height,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            is_animating=(frame_count > 1),
        ),
    )
    world.add_component(entity, Selectable())
    has_shadow = type_id == "ball"
    world.add_component(entity, VisualTransform(has_drop_shadow=has_shadow))
    world.add_component(entity, StableIDComponent(id=world.get_next_stable_id()))
    world.add_component(entity, Persistable())

    stats = ItemStats(
        name=_get_attr(data, "name", "Item"),
        type_id=type_id,
        cost=_get_attr(data, "cost", 10),
        nutrition=_get_attr(data, "nutrition", 0) or 0,
        fun=_get_attr(data, "fun", 0) or 0,
        comfort=_get_attr(data, "comfort", 0) or 0,
        is_portable=_get_attr(data, "is_portable", False),
    )
    world.add_component(entity, stats)

    # Lighting Components
    light_radius = _get_attr(data, "light_radius", None)
    if light_radius:
        color = tuple(_get_attr(data, "light_color", [255, 255, 255]))
        intensity = _get_attr(data, "light_intensity", 1.0)
        flicker_str = _get_attr(data, "light_flicker", "NONE")
        flicker_style = FlickerStyle.NONE
        if flicker_str == "FIRE":
            flicker_style = FlickerStyle.FIRE
        elif flicker_str == "PULSE":
            flicker_style = FlickerStyle.PULSE

        world.add_component(
            entity,
            LightSource(
                radius=light_radius,
                color=color,
                intensity=intensity,
                flicker_style=flicker_style,
            ),
        )

    is_occluder = _get_attr(data, "occluder", False)
    if is_occluder:
        # Occluder without polygon defaults to physics shape
        # Assume static if it's an occluder item (like a wall segment or furniture)
        is_static = _get_attr(data, "static_occluder", True)
        world.add_component(entity, Occluder(static=is_static))

    if physics_system:
        mass = 1
        # Box shape for items
        inertia = pymunk.moment_for_box(mass, (width, height))
        body = pymunk.Body(mass, inertia)
        shape = pymunk.Poly.create_box(body, (width, height))
        body.position = (x, y)
        shape.elasticity = 0.5
        shape.friction = 0.5
        shape.filter = pymunk.ShapeFilter(
            categories=CollisionCategories.ITEM,
            mask=CollisionCategories.HIGH_OBSTACLE
            | CollisionCategories.POOP
            | CollisionCategories.ITEM,
            group=entity,
        )
        physics_system.space.add(body, shape)
        world.add_component(entity, PhysicsBody(body=body, shape=shape))

    # Navigation Obstacle Registration
    # Check if this item should block navigation
    obstacle_str = _get_attr(data, "obstacle_type", None)
    if obstacle_str:
        nav_service = world.services.try_get(NavigationService)
        if nav_service:
            obs_type = ObstacleType.HIGH
            if obstacle_str.upper() == "LOW":
                obs_type = ObstacleType.LOW

            # Use rect-based registration for better coverage
            nav_service.update_obstacle_rect(
                x,
                y,
                float(width),
                float(height),
                walkable=False,
                obstacle_type=obs_type,
            )

    return entity


def create_poop(world: World, x: float, y: float) -> int:
    """
    Creates a Poop entity.

    Args:
        world (World): The ECS World.
        x (float): World x-coordinate.
        y (float): World y-coordinate.

    Returns:
        int: The created entity ID.
    """
    physics_system = world.services.try_get(PhysicsSystem)

    entity = world.create_entity()
    world.add_component(entity, Transform(x=x, y=y))
    world.add_component(entity, Sprite(image_name="poop.png", width=32, height=32))
    world.add_component(entity, Selectable())
    world.add_component(entity, Poop())
    world.add_component(entity, VisualTransform())

    if physics_system:
        mass = 1
        radius = 10
        inertia = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, inertia)
        shape = pymunk.Circle(body, radius)
        body.position = (x, y)
        shape.elasticity = 0.2
        shape.friction = 0.8
        shape.filter = pymunk.ShapeFilter(
            categories=CollisionCategories.POOP, mask=CollisionCategories.ALL
        )
        # EntityFactory did not set userdata, so we don't either.
        physics_system.space.add(body, shape)
        world.add_component(entity, PhysicsBody(body=body, shape=shape))

    return entity
