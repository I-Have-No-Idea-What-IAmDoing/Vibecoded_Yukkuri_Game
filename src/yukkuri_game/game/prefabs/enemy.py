"""
Prefab for Enemy entities.
"""

from ...engine.ecs import World
from .yukkuri import create_yukkuri


def create_enemy(world: World, type_id: str, x: float, y: float, **kwargs) -> int:
    """
    Creates an Enemy entity.
    Currently wraps create_yukkuri as Yukkuris are the primary agents.
    """
    # We could add an "Enemy" tag component here if needed.
    return create_yukkuri(world, type_id, x, y, **kwargs)
