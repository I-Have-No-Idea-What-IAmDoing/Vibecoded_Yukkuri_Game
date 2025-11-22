from ...engine.ecs import System, World
from ...game.components import FloatingText, Transform

class FloatingTextSystem(System):
    """
    System responsible for updating floating text entities (movement and lifetime).
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the position and age of floating text entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        entities = world.get_entities_with(FloatingText, Transform)

        # Collect entities to destroy to avoid modifying list while iterating (though get_entities_with returns a list copy usually, but safe is better)
        to_destroy = []

        for entity in entities:
            ft = world.get_component(entity, FloatingText)
            transform = world.get_component(entity, Transform)

            # Update age
            ft.age += dt

            # Check lifetime
            if ft.age >= ft.lifetime:
                to_destroy.append(entity)
                continue

            # Update position
            transform.x += ft.dx * dt
            transform.y += ft.dy * dt

        for entity in to_destroy:
            world.destroy_entity(entity)
