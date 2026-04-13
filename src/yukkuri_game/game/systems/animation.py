"""
Animation System - Sprite Animation Management.

Handles sprite animation states, frame updates, and rendering for entities.
Driven by state changes (idle, walk, run, etc.) and time deltas.

Components:
-   Animator: Stores current animation state and playback parameters.
-   AnimationSystem: Updates Animator and Sprite components based on game time.

Features:
-   State-based animations (mapped to rows/indices in sprite sheet).
-   Variable animation speeds.
-   Looping or one-shot playback.
-   Horizontal flipping for direction facing.
-   Visual debug rendering of collision shapes (if enabled).

Data Structure:
-   Animation definitions are loaded from TOML via ResourceManager.
-   Sprite sheets are standard grids of frames.
"""

from typing import Any, cast

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.resource_manager import ResourceManager
from ..components import Animator, LODComponent, Sprite
from ..events import AnimationEvent
from ..yukkuri_components import AIState, YukkuriStats


class AnimationSystem(System):
    """
    Animation System - Sprite Animation Management.

    Handles sprite animation states, frame updates, and rendering for entities.
    Driven by state changes (idle, walk, run, etc.) and time deltas.
    """

    def __init__(self, event_bus: EventBus | None = None):
        """
        Initializes the AnimationSystem.

        Args:
            event_bus (EventBus | None): The event bus.
        """
        self.event_bus = event_bus
        self.frame_count: int = 0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the animation state of all entities with a Sprite component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        self.frame_count += 1

        # Handle Animator components (Advanced Animation)
        for entity_id, (sprite, animator) in world.get_components_tuple(
            Sprite, Animator
        ):
            # Check LOD
            lod = world.try_get_component(entity_id, LODComponent)
            if lod:
                # Level 1 (Med): Update every 2nd frame
                if lod.level == 1 and self.frame_count % 2 != 0:
                    continue
                # Level 2 (Low): Update every 4th frame
                elif lod.level == 2 and self.frame_count % 4 != 0:
                    continue
                # Level 3 (Culled): Skip animation updates
                elif lod.level >= 3:
                    continue

            # Apply Agility Modifier to Animation Speed
            stats = world.try_get_component(entity_id, YukkuriStats)
            agility_mod = min(1.5, stats.agility) if stats else 1.0

            self._update_animator(entity_id, animator, sprite, dt * agility_mod)

            # Sync with AI State if available
            ai_state = world.get_component(entity_id, AIState)
            if ai_state:
                self._sync_ai_animation(world, entity_id, animator, ai_state)

        # Legacy sprite animation fallback when no Animator is present.
        rm = world.services.try_get(ResourceManager)

        for entity, sprite in world.get_components(Sprite).items():
            if world.has_component(entity, Animator):
                continue

            # Check LOD for basic sprites too
            lod = world.try_get_component(entity, LODComponent)
            if lod:
                if lod.level == 1 and self.frame_count % 2 != 0:
                    continue
                elif lod.level == 2 and self.frame_count % 4 != 0:
                    continue
                elif lod.level >= 3:
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
                            animator.current_frame_index = 0
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
        This runs only for entities without an Animator component.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            sprite (Sprite): The sprite component.
            rm (ResourceManager | None): The resource manager.
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
        base_image = None

        # Pull from ResourceManager
        base_image = None
        yukkuri_type = rm.yukkuri_types.get(stats.type_id)
        if not yukkuri_type:
            return

        if isinstance(yukkuri_type, dict):
            base_image = cast(str | None, yukkuri_type.get(cast(Any, "image"), None))
        else:
            base_image = cast(str | None, getattr(yukkuri_type, "image", None))

        if not base_image:
            return

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
