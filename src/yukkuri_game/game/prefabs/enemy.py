"""
Prefab for Enemy entities.
"""

from ...engine.ecs import World
from .yukkuri import create_yukkuri


def create_enemy(world: World, type_id: str, x: float, y: float, **kwargs) -> int:
    """
    Creates an Enemy entity.
    Currently wraps create_yukkuri as Yukkuris are the primary agents.

    Args:
        world (World): The ECS World instance.
        type_id (str): The type identifier for the enemy.
        x (float): The x-coordinate.
        y (float): The y-coordinate.
        **kwargs: Additional arguments passed to create_yukkuri.

    Returns:
        int: The ID of the created entity.
    """
    # We could add an "Enemy" tag component here if needed.
    return create_yukkuri(world, type_id, x, y, **kwargs)
