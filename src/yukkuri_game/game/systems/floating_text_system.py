from ...engine.ecs import System, World
from ..components import Transform, FloatingText

class FloatingTextSystem(System):
    """
    System that updates floating text entities.
    """
    def update(self, world: World, dt: float) -> None:
        """
        Updates the position and lifetime of floating text entities.

        Args:
            world (World): The ECS world.
            dt (float): Delta time in seconds.
        """
        entities = world.get_entities_with(Transform, FloatingText)
        for entity in entities:
            transform = world.get_component(entity, Transform)
            text_comp = world.get_component(entity, FloatingText)

            # Update age
            text_comp.age += dt

            # Remove if expired
            if text_comp.age >= text_comp.lifetime:
                world.destroy_entity(entity)
                continue

            # Move up
            transform.y += text_comp.velocity_y * dt
