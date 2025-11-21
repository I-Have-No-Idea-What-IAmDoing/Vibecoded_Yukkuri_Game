from ...engine.ecs import System, World
from ..components import Sprite

class AnimationSystem(System):
    """
    System that updates the animation state of sprites.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the current frame of animated sprites.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        entities = world.get_entities_with(Sprite)
        for ent in entities:
            sprite = world.get_component(ent, Sprite)
            if sprite and sprite.frame_count > 1 and sprite.animation_speed > 0:
                sprite.timer += dt
                while sprite.timer >= sprite.animation_speed:
                    sprite.timer -= sprite.animation_speed
                    sprite.current_frame = (sprite.current_frame + 1) % sprite.frame_count
