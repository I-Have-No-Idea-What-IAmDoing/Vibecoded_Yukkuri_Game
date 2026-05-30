"""
Physics Reconstruction System.
"""

import pymunk
from ...engine.ecs import World
from ..components import ItemStats, Poop, YukkuriStats
from ...engine.components import PhysicsBody, Transform
from ..collision_constants import CollisionCategories
from ..physics_utils import add_physics_body, get_yukkuri_radius


def reconstruct_physics(world: World) -> None:
    """
    Iterates over entities that need physics bodies but don't have them (e.g. after load).
    Recreates Pymunk bodies and shapes based on entity components.

    Args:
        world (World): The ECS World.

    Returns:
        None
    """
    # Reconstruct Yukkuris
    for entity, (transform, stats) in world.get_components_tuple(
        Transform, YukkuriStats
    ):
        if world.has_component(entity, PhysicsBody):
            continue

        add_physics_body(
            world=world,
            entity=entity,
            shape_type="circle",
            mass=10.0,
            position=(transform.x, transform.y),
            radius_or_size=get_yukkuri_radius(stats.growth_stage),
            collision_category=CollisionCategories.GROUND_UNIT,
            collision_mask=CollisionCategories.HIGH_OBSTACLE
            | CollisionCategories.GROUND_UNIT
            | CollisionCategories.POOP,
            elasticity=0.5,
            friction=0.5,
            set_userdata=True,
            body_type=pymunk.Body.KINEMATIC,
        )

    # Reconstruct Poops
    for entity, (transform, poop) in world.get_components_tuple(Transform, Poop):
        if world.has_component(entity, PhysicsBody):
            continue

        add_physics_body(
            world=world,
            entity=entity,
            shape_type="circle",
            mass=1.0,
            position=(transform.x, transform.y),
            radius_or_size=10.0,
            collision_category=CollisionCategories.POOP,
            collision_mask=CollisionCategories.ALL,
            elasticity=0.2,
            friction=0.8,
            body_type=pymunk.Body.DYNAMIC,
        )

    # Reconstruct Items
    from ...engine.resource_manager import ResourceManager
    from ..ai.navigation_service import NavigationService, ObstacleType

    rm = world.services.try_get(ResourceManager)
    nav_service = world.services.try_get(NavigationService)

    for entity, (transform, stats) in world.get_components_tuple(Transform, ItemStats):
        if world.has_component(entity, PhysicsBody):
            continue

        width, height = 32, 32
        obstacle_str = None
        if rm:
            data = rm.item_types.get(stats.type_id)
            if data:
                width = getattr(data, "width", 32)
                height = getattr(data, "height", 32)
                obstacle_str = getattr(data, "obstacle_type", None)

        add_physics_body(
            world=world,
            entity=entity,
            shape_type="box",
            mass=1.0,
            position=(transform.x, transform.y),
            radius_or_size=(width, height),
            collision_category=CollisionCategories.ITEM,
            collision_mask=CollisionCategories.HIGH_OBSTACLE
            | CollisionCategories.POOP
            | CollisionCategories.ITEM,
            elasticity=0.5,
            friction=0.5,
            body_type=pymunk.Body.DYNAMIC,
        )

        # Re-register obstacle items on the navigation grid
        if obstacle_str and nav_service:
            obs_type = ObstacleType.HIGH
            if isinstance(obstacle_str, str) and obstacle_str.upper() == "LOW":
                obs_type = ObstacleType.LOW
            nav_service.update_obstacle_rect(
                transform.x,
                transform.y,
                float(width),
                float(height),
                walkable=False,
                obstacle_type=obs_type,
            )
