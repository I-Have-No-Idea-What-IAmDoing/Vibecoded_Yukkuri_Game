"""
Prefab for visual effects.
"""
from ...engine.ecs import World
from ..components import Transform, FloatingText

def create_floating_text(world: World, x: float, y: float, text: str, color: tuple[int, int, int], size: int = 20, lifetime: float = 2.0, velocity_y: float = -50.0) -> int:
    """
    Creates a floating text entity.
    """
    entity = world.create_entity()
    world.add_component(entity, Transform(x=x, y=y))
    world.add_component(entity, FloatingText(
        text=text, color=color, lifetime=lifetime, max_lifetime=lifetime,
        velocity_y=velocity_y, size=size
    ))
    return entity
