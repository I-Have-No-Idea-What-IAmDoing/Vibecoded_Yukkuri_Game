from ..engine.ecs import System, World
from ..components import Transform, FloatingText

class FloatingTextSystem(System):
    """
    System to manage floating text entities.
    Updates their position based on velocity and handles their lifetime.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the floating text entities.

        Args:
            world (World): The ECS World instance.
            dt (float): Delta time since the last frame.
        """
        entities_to_remove = []

        for entity, (transform, floating_text) in world.get_components(Transform, FloatingText):
            # Update lifetime
            floating_text.lifetime -= dt
            if floating_text.lifetime <= 0:
                entities_to_remove.append(entity)
                continue

            # Update position
            transform.x += floating_text.velocity[0] * dt
            transform.y += floating_text.velocity[1] * dt

        # Remove dead entities
        for entity in entities_to_remove:
            world.delete_entity(entity)
