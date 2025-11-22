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
        entities = world.get_entities_with(Transform, FloatingText)
        for entity in entities:
            transform = world.get_component(entity, Transform)
            text_comp = world.get_component(entity, FloatingText)

            if transform and text_comp:
                # Move up
                transform.y += text_comp.velocity_y * dt

                # Decrease lifetime
                text_comp.lifetime -= dt

                # Destroy if expired
                if text_comp.lifetime <= 0:
                    world.destroy_entity(entity)
