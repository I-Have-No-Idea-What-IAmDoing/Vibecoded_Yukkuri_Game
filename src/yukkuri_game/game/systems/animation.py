from ...engine.ecs import System, World
from ..components import Sprite, Animator
from ..yukkuri_components import AIState

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

        # Handle Animator components (Advanced Animation)
        # Note: World.get_components retrieves a dict for a single type.
        # For multiple types, we should use get_components_tuple (which wraps esper.get_components)
        # or loop and check.
        # Based on ecs.py, get_components_tuple is the wrapper for esper.get_components(*types)

        for entity, (sprite, animator) in world.get_components_tuple(Sprite, Animator):
            self._update_animator(animator, sprite, dt)

            # Sync with AI State if available
            ai_state = world.get_component(entity, AIState)
            if ai_state:
                self._sync_ai_animation(animator, ai_state)

        # Handle Legacy Sprite Animation (if no Animator)
        for entity, sprite in world.get_components(Sprite).items():
            if world.has_component(entity, Animator):
                continue

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

    def _update_animator(self, animator: Animator, sprite: Sprite, dt: float) -> None:
        """
        Updates the Animator component and syncs it to the Sprite.
        """
        current_anim_def = animator.animations.get(animator.current_animation)
        if not current_anim_def:
            return

        # Apply animation properties to sprite (one-time or continuous check)
        # To avoid constant assignment, we could check if changed, but assignment is cheap.
        if current_anim_def.image:
            sprite.image_name = current_anim_def.image
        if current_anim_def.width is not None:
            sprite.width = current_anim_def.width
        if current_anim_def.height is not None:
            sprite.height = current_anim_def.height

        if animator.finished:
            return

        animator.timer += dt

        while animator.timer >= current_anim_def.frame_duration:
            animator.timer -= current_anim_def.frame_duration
            animator.current_frame_index += 1

            if animator.current_frame_index >= len(current_anim_def.frames):
                if current_anim_def.loop:
                    animator.current_frame_index = 0
                else:
                    animator.current_frame_index = len(current_anim_def.frames) - 1
                    animator.finished = True
                    break

        # Sync to Sprite
        # Assumes frames list contains indices into the sprite sheet
        if 0 <= animator.current_frame_index < len(current_anim_def.frames):
            sprite.current_frame = current_anim_def.frames[animator.current_frame_index]

    def _sync_ai_animation(self, animator: Animator, ai_state: AIState) -> None:
        """
        Syncs the current animation based on the AI state.
        """
        # Simple mapping: AI action name -> Animation name
        # Normalize names to lower case for comparison if needed, but let's assume exact match or simple mapping

        target_anim = ai_state.current_action.lower()

        # If the animation exists and is different from current, switch
        if target_anim in animator.animations and target_anim != animator.current_animation:
            animator.current_animation = target_anim
            animator.current_frame_index = 0
            animator.timer = 0.0
            animator.finished = False
