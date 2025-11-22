from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import Sprite, Animator
from ..yukkuri_components import AIState
from ..events import AnimationEvent

class AnimationSystem(System):
    """
    System responsible for updating sprite animations.
    """

    def __init__(self, event_bus: EventBus = None):
        """
        Initializes the AnimationSystem.

        Args:
            event_bus (EventBus, optional): The event bus to publish animation events to.
        """
        self.event_bus = event_bus

    def update(self, world: World, dt: float) -> None:
        """
        Updates the animation state of all entities with a Sprite component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """

        # Handle Animator components (Advanced Animation)
        for entity, (sprite, animator) in world.get_components_tuple(Sprite, Animator):
            # Sync with AI State if available
            ai_state = world.get_component(entity, AIState)
            if ai_state:
                self._sync_ai_animation(animator, ai_state)

            self._update_animator(entity, animator, sprite, dt)

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
                        break

    def _update_animator(self, entity_id: int, animator: Animator, sprite: Sprite, dt: float) -> None:
        """
        Updates the Animator component and syncs it to the Sprite.
        """
        current_anim_def = animator.animations.get(animator.current_animation)
        if not current_anim_def:
            return

        # Apply animation properties to sprite
        if current_anim_def.image:
            sprite.image_name = current_anim_def.image
        if current_anim_def.width is not None:
            sprite.width = current_anim_def.width
        if current_anim_def.height is not None:
            sprite.height = current_anim_def.height

        if animator.finished:
            # Check for auto-transition
            if animator.next_animation and animator.next_animation in animator.animations:
                self._switch_animation(animator, animator.next_animation)
            return

        # Apply speed multiplier
        effective_dt = dt * animator.speed
        animator.timer += effective_dt

        while animator.timer >= current_anim_def.frame_duration:
            animator.timer -= current_anim_def.frame_duration

            # Determine next frame index
            frame_changed = False
            if current_anim_def.ping_pong:
                if animator.forward:
                    animator.current_frame_index += 1
                    if animator.current_frame_index >= len(current_anim_def.frames):
                        animator.current_frame_index -= 2 # Go back
                        animator.forward = False
                        if animator.current_frame_index < 0: # Single frame ping-pong edge case
                            animator.current_frame_index = 0
                            animator.forward = True
                else:
                    animator.current_frame_index -= 1
                    if animator.current_frame_index < 0:
                        animator.current_frame_index = 1 # Go forward
                        animator.forward = True
                        if animator.current_frame_index >= len(current_anim_def.frames):
                             animator.current_frame_index = 0 # Should not happen unless len=1
            else:
                # Standard loop or single play
                animator.current_frame_index += 1
                if animator.current_frame_index >= len(current_anim_def.frames):
                    if current_anim_def.loop:
                        animator.current_frame_index = 0
                    else:
                        animator.current_frame_index = len(current_anim_def.frames) - 1
                        animator.finished = True

            frame_changed = True

            # Trigger Event if defined for this frame
            if frame_changed and self.event_bus:
                event_name = current_anim_def.events.get(animator.current_frame_index)
                if event_name:
                    self.event_bus.publish(AnimationEvent(
                        entity_id=entity_id,
                        event_name=event_name,
                        animation_name=animator.current_animation,
                        frame_index=animator.current_frame_index
                    ))

            if animator.finished:
                 break

        # Sync to Sprite
        if 0 <= animator.current_frame_index < len(current_anim_def.frames):
            sprite.current_frame = current_anim_def.frames[animator.current_frame_index]

        # Check for auto-transition immediately if finished
        if animator.finished:
            if animator.next_animation and animator.next_animation in animator.animations:
                self._switch_animation(animator, animator.next_animation)
                # Update the sprite immediately for the new animation
                new_anim_def = animator.animations[animator.current_animation]
                if 0 <= animator.current_frame_index < len(new_anim_def.frames):
                     sprite.current_frame = new_anim_def.frames[animator.current_frame_index]

    def _switch_animation(self, animator: Animator, new_anim: str) -> None:
        """Helper to switch animation state cleanly."""
        animator.current_animation = new_anim
        animator.current_frame_index = 0
        animator.timer = 0.0
        animator.finished = False
        animator.forward = True

    def _sync_ai_animation(self, animator: Animator, ai_state: AIState) -> None:
        """
        Syncs the current animation based on the AI state.
        """
        target_anim = ai_state.current_action.lower()

        if target_anim in animator.animations and target_anim != animator.current_animation:
            self._switch_animation(animator, target_anim)
