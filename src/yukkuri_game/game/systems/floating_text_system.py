import pygame
from ...engine.ecs import System, World
from ..components import Transform, FloatingText

class FloatingTextSystem(System):
    """
    System that handles the movement and lifetime of floating text entities.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates floating text entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Iterate over all entities with FloatingText and Transform
        for entity, (text_comp, transform) in world.get_components_tuple(FloatingText, Transform):
            # Update age
            text_comp.age += dt

            # Remove if expired
            if text_comp.age >= text_comp.lifetime:
                world.destroy_entity(entity)
                continue

            # Update position (move up)
            transform.y += text_comp.velocity_y * dt
