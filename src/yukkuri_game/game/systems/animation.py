"""
Module defining the AnimationSystem logic.
"""

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.resource_manager import ResourceManager
from ..components import Sprite, Animator
from ..yukkuri_components import AIState, YukkuriStats
from ..events import AnimationEvent


class AnimationSystem(System):
    """
    System responsible for updating sprite animations.

    Attributes:
        event_bus (Optional[EventBus]): The event bus to publish animation events to.
    """

    def __init__(self, event_bus: EventBus | None = None):
        """
        Initializes the AnimationSystem.

        Args:
            event_bus (Optional[EventBus]): The event bus to publish animation events to.
        """
        self.event_bus = event_bus

    def update(self, world: World, dt: float) -> None:
        """
        Updates the animation state of all entities with a Sprite component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """

        # Handle Animator components (Advanced Animation)
        for entity, (sprite, animator) in world.get_components_tuple(Sprite, Animator):
            self._update_animator(entity, animator, sprite, dt)

            # Sync with AI State if available
            ai_state = world.get_component(entity, AIState)
            if ai_state:
                self._sync_ai_animation(world, entity, animator, ai_state)

        # Handle Legacy Sprite Animation (if no Animator)

        # Retrieve ResourceManager once
        rm = world.services.try_get(ResourceManager)

        for entity, sprite in world.get_components(Sprite).items():
            if world.has_component(entity, Animator):
                continue

            # Dynamic Sprite Switching based on AIState (if no Animator)
            self._update_dynamic_sprite(world, entity, sprite, rm)

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

    def _update_animator(
        self, entity_id: int, animator: Animator, sprite: Sprite, dt: float
    ) -> None:
        """
        Updates the Animator component and syncs it to the Sprite.

        Args:
            entity_id (int): The entity ID.
            animator (Animator): The animator component.
            sprite (Sprite): The sprite component.
            dt (float): Delta time.

        Returns:
            None
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
            if (
                animator.next_animation
                and animator.next_animation in animator.animations
            ):
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
                        animator.current_frame_index -= 2  # Go back
                        animator.forward = False
                        if (
                            animator.current_frame_index < 0
                        ):  # Single frame ping-pong edge case
                            animator.current_frame_index = 0
                            animator.forward = True
                else:
                    animator.current_frame_index -= 1
                    if animator.current_frame_index < 0:
                        animator.current_frame_index = 1  # Go forward
                        animator.forward = True
                        if animator.current_frame_index >= len(current_anim_def.frames):
                            animator.current_frame_index = (
                                0  # Should not happen unless len=1
                            )
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
                    self.event_bus.publish(
                        AnimationEvent(
                            entity_id=entity_id,
                            event_type=event_name,
                            animation_name=animator.current_animation,
                            frame_index=animator.current_frame_index,
                        )
                    )

            if animator.finished:
                break

        # Sync to Sprite
        if 0 <= animator.current_frame_index < len(current_anim_def.frames):
            sprite.current_frame = current_anim_def.frames[animator.current_frame_index]

        # Check for auto-transition immediately if finished
        if animator.finished:
            if (
                animator.next_animation
                and animator.next_animation in animator.animations
            ):
                self._switch_animation(animator, animator.next_animation)
                # Update the sprite immediately for the new animation
                new_anim_def = animator.animations[animator.current_animation]
                if 0 <= animator.current_frame_index < len(new_anim_def.frames):
                    sprite.current_frame = new_anim_def.frames[
                        animator.current_frame_index
                    ]

    def _switch_animation(self, animator: Animator, new_anim: str) -> None:
        """
        Helper to switch animation state cleanly.

        Args:
            animator (Animator): The animator component.
            new_anim (str): The name of the new animation.

        Returns:
            None
        """
        animator.current_animation = new_anim
        animator.current_frame_index = 0
        animator.timer = 0.0
        animator.finished = False
        animator.forward = True

    def _sync_ai_animation(
        self, world: World, entity: int, animator: Animator, ai_state: AIState
    ) -> None:
        """
        Syncs the current animation based on the AI state.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            animator (Animator): The animator component.
            ai_state (AIState): The AIState component.

        Returns:
            None
        """
        target_anim = ai_state.current_action.lower()

        # Flight Overrides
        from ..yukkuri_components import Flight, FlightState

        flight = world.try_get_component(entity, Flight)
        if flight:
            if flight.state == FlightState.SWOOPING:
                target_anim = "swoop"
            elif flight.state in (
                FlightState.FLYING,
                FlightState.TAKEOFF,
                FlightState.HOVERING,
            ):
                target_anim = "fly"
                # Special case: If action is "Hunt" and we are flying -> "hunt_fly"?
                # For now, "fly" takes precedence to show they are airborne.

        if (
            target_anim in animator.animations
            and target_anim != animator.current_animation
        ):
            self._switch_animation(animator, target_anim)

    def _update_dynamic_sprite(
        self, world: World, entity: int, sprite: Sprite, rm: ResourceManager | None
    ) -> None:
        """
        Updates the sprite image based on AIState if no Animator is present.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            sprite (Sprite): The sprite component.
            rm (Optional[ResourceManager]): The resource manager.

        Returns:
            None
        """
        if not rm:
            return

        ai_state = world.get_component(entity, AIState)
        if not ai_state:
            return

        # Get base image from YukkuriStats -> ResourceManager
        stats = world.get_component(entity, YukkuriStats)
        if not stats:
            return

        # Determine base image name
        # We need to look up the type definition
        # rm.yukkuri_types is a dict of YukkuriType
        yukkuri_type = rm.yukkuri_types.get(stats.type_id)
        if not yukkuri_type:
            return

        base_image = yukkuri_type.image

        # Determine target image based on action
        action = ai_state.current_action
        if action == "Idle":
            target_image = base_image
        else:
            # Construct name: e.g., "reimu.png" -> "reimu_sleeping.png"
            if "." in base_image:
                name, ext = base_image.rsplit(".", 1)
                target_image = f"{name}_{action.lower()}.{ext}"
            else:
                target_image = f"{base_image}_{action.lower()}"

        # Update sprite if changed
        if sprite.image_name != target_image:
            sprite.image_name = target_image
