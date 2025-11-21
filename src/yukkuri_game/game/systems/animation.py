from ...engine.ecs import System, World
from ..components import Sprite

class AnimationSystem(System):
    """
    System responsible for updating sprite animations.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates the animation state of all entities with a Sprite component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        for entity, sprite in world.get_components(Sprite).items():

            # Check for animation switch
            if sprite.current_animation and sprite.current_animation in sprite.animations:
                # Detect switch using explicit tracking
                if sprite.current_animation != sprite._last_animation:
                    anim = sprite.animations[sprite.current_animation]

                    # Apply animation settings
                    sprite.row = anim.row
                    sprite.start_frame = anim.start_frame
                    sprite.frame_count = anim.frame_count
                    sprite.frame_duration = anim.frame_duration
                    sprite.loop = anim.loop

                    # Reset playback state
                    sprite.current_frame = 0 # Start from beginning relative to start_frame
                    sprite.timer = 0.0
                    sprite.is_animating = True

                    # Update internal tracker
                    sprite._last_animation = sprite.current_animation

            if not sprite.is_animating or sprite.frame_count <= 1:
                continue

            sprite.timer += dt
            while sprite.timer >= sprite.frame_duration:
                sprite.timer -= sprite.frame_duration
                sprite.current_frame += 1

                if sprite.current_frame >= sprite.frame_count:
                    if sprite.loop:
                        sprite.current_frame = 0
                    else:
                        sprite.current_frame = sprite.frame_count - 1
                        sprite.is_animating = False
                        # No need to process more frames if animation ended
                        break
