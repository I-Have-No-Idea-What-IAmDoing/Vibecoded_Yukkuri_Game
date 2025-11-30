"""
Module defining the InteractionSystem logic.
"""
import math
from typing import Optional
from loguru import logger
from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, ItemStats, AIState, Personality, EmotionalState
from ..trait_service import TraitService

class InteractionSystem(System):
    """
    System responsible for handling entity interactions (e.g. eating, sleeping).

    Attributes:
        audio (Optional[AudioManager]): The audio manager instance.
        trait_service (Optional[TraitService]): The trait service.
    """
    def __init__(self) -> None:
        """Initializes the InteractionSystem."""
        super().__init__()
        self.audio: Optional[AudioManager] = None
        self.trait_service: Optional[TraitService] = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the interaction system.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        # Get all entities with InteractionRequest
        # We need to iterate safely because we might remove components
        entities = list(world.get_components_tuple(InteractionRequest, Transform, YukkuriStats))

        for entity, (request, transform, stats) in entities:
            self._handle_interaction(world, entity, request, transform, stats)

            # Remove request after processing
            if world.has_component(entity, InteractionRequest):
                world.remove_component(entity, InteractionRequest)

    def _check_predation_allowed(self, world: World, entity: int) -> bool:
        """
        Checks if the entity has permission to eat other Yukkuris (Predation).

        Args:
            world (World): The ECS World.
            entity (int): The entity ID checking permission.

        Returns:
            bool: True if allowed, False otherwise.
        """
        personality = world.get_component(entity, Personality)
        if personality and self.trait_service:
            if personality.cached_overrides is None:
                personality.cached_overrides = self.trait_service.calculate_overrides(personality.traits)

            # Check for "can_eat_yukkuri" override
            if personality.cached_overrides and personality.cached_overrides.get("can_eat_yukkuri", False):
                return True
        return False

    def _handle_interaction(self, world: World, entity: int, request: InteractionRequest,
                            transform: Transform, stats: YukkuriStats) -> None:
        """
        Handles a single interaction request.

        Args:
            world (World): The ECS World.
            entity (int): The requesting entity ID.
            request (InteractionRequest): The request component.
            transform (Transform): The requesting entity's transform.
            stats (YukkuriStats): The requesting entity's stats.

        Returns:
            None
        """
        target_id = request.target_id

        if not world.entity_exists(target_id):
            return

        target_transform = world.get_component(target_id, Transform)
        if not target_transform:
            return

        # Verify distance (sanity check)
        dist = math.hypot(transform.x - target_transform.x, transform.y - target_transform.y)
        if dist > 50.0: # Slightly larger than action threshold to account for movement
            return

        # Handle Interaction with another Yukkuri (Predation)
        target_stats = world.get_component(target_id, YukkuriStats)
        if target_stats and request.consume:
            if self._check_predation_allowed(world, entity):
                # Execute Predation
                stats.hunger = max(0, stats.hunger - 50.0) # Big meal
                if self.audio:
                    self.audio.play_sound("eat") # Crunch?

                world.destroy_entity(target_id)
                ai = world.get_component(entity, AIState)
                if ai and ai.current_target_id == target_id:
                    ai.current_target_id = -1
                logger.info(f"Entity {entity} ate Yukkuri {target_id} (Predation).")
            else:
                logger.debug(f"Entity {entity} attempted to eat Yukkuri {target_id} but lacks permission/trait.")
            return

        # Handle Interaction with Item
        item_stats = world.get_component(target_id, ItemStats)
        if item_stats:
            if item_stats.nutrition > 0:
                stats.hunger = max(0, stats.hunger - item_stats.nutrition)

            if item_stats.fun > 0:
                emotional = world.get_component(entity, EmotionalState)
                if emotional:
                    emotional.happiness = min(100, emotional.happiness + item_stats.fun)

            if item_stats.comfort > 0:
                stats.energy = min(100, stats.energy + item_stats.comfort)

            if request.consume:
                if self.audio:
                    self.audio.play_sound("eat")

                # Destroy the item
                world.destroy_entity(target_id)

                # Update consumer AI state if needed (e.g. reset target)
                ai = world.get_component(entity, AIState)
                if ai and ai.current_target_id == target_id:
                    ai.current_target_id = -1
