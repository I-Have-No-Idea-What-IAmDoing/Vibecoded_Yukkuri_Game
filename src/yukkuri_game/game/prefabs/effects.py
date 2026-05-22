"""
Prefab for visual effects.
"""

from ...engine.ecs import World
from yukkuri_game.engine.components import Transform, FloatingText


def create_floating_text(
    world: World,
    x: float,
    y: float,
    text: str,
    color: tuple[int, int, int],
    size: int = 20,
    lifetime: float = 2.0,
    velocity_y: float = -50.0,
) -> int:
    """
    Creates a floating text entity.

    Args:
        world (World): The ECS World instance.
        x (float): The x-coordinate for the text.
        y (float): The y-coordinate for the text.
        text (str): The text content to display.
        color (tuple[int, int, int]): The RGB color of the text.
        size (int, optional): The font size. Defaults to 20.
        lifetime (float, optional): The duration the text remains visible in seconds. Defaults to 2.0.
        velocity_y (float, optional): The vertical velocity of the text. Defaults to -50.0.

    Returns:
        int: The ID of the created entity.
    """
    if getattr(world, "_updating", False):
        entity = world.commands.create_entity(
            Transform(x=x, y=y),
            FloatingText(
                text=text,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                velocity_y=velocity_y,
                size=size,
            ),
        )
    else:
        entity = world.create_entity()
        world.add_component(entity, Transform(x=x, y=y))
        world.add_component(
            entity,
            FloatingText(
                text=text,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                velocity_y=velocity_y,
                size=size,
            ),
        )
    return entity
