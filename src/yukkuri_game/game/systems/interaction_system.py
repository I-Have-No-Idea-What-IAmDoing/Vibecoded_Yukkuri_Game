"""
Module defining the InteractionSystem logic.
"""

import math
from loguru import logger
from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import Transform, InteractionRequest
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    ItemStats,
    AIState,
    Personality,
)
from ..trait_service import TraitService
from .hunger_system import HungerSystem
from .social_system import SocialSystem


class InteractionSystem(System):
    """
    System responsible for handling entity interactions.
    Acts as a dispatcher to specific systems (Hunger, Social) or handles generic interactions.

    Attributes:
        audio (Optional[AudioManager]): The audio manager instance.
        trait_service (Optional[TraitService]): The trait service.
        hunger_system (Optional[HungerSystem]): The hunger system.
        social_system (Optional[SocialSystem]): The social system.
    """

    def __init__(self) -> None:
        """Initializes the InteractionSystem."""
        super().__init__()
        self.audio: AudioManager | None = None
        self.trait_service: TraitService | None = None
        self.hunger_system: HungerSystem | None = None
        self.social_system: SocialSystem | None = None

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
        if self.hunger_system is None:
            self.hunger_system = world.services.try_get(HungerSystem)
        if self.social_system is None:
            self.social_system = world.services.try_get(SocialSystem)

        # Get all entities with InteractionRequest
        # We need to iterate safely because we might remove components
        entities = list(
            world.get_components_tuple(InteractionRequest, Transform, YukkuriStats)
        )

        for entity, (request, transform, stats) in entities:
            handled = self._handle_interaction(world, entity, request, transform, stats)

            # Remove request only if handled
            if handled and world.has_component(entity, InteractionRequest):
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
                personality.cached_overrides = self.trait_service.calculate_overrides(
                    personality.traits
                )

            # Check for "can_eat_yukkuri" override
            if personality.cached_overrides and personality.cached_overrides.get(
                "can_eat_yukkuri", False
            ):
                return True
        return False

    def _handle_interaction(
        self,
        world: World,
        entity: int,
        request: InteractionRequest,
        transform: Transform,
        stats: YukkuriStats,
    ) -> bool:
        """
        Handles a single interaction request.

        Args:
            world (World): The ECS World.
            entity (int): The requesting entity ID.
            request (InteractionRequest): The request component.
            transform (Transform): The requesting entity's transform.
            stats (YukkuriStats): The requesting entity's stats.

        Returns:
            bool: True if the request was handled and should be removed.
        """
        target_id = request.target_id

        if not world.entity_exists(target_id):
            # Target is gone, invalid request -> remove it
            return True

        target_transform = world.get_component(target_id, Transform)
        if not target_transform:
            # Target invalid, remove request
            return True

        # Verify distance (sanity check)
        dist = math.hypot(
            transform.x - target_transform.x, transform.y - target_transform.y
        )
        if dist > 50.0:  # Slightly larger than action threshold to account for movement
            # Too far, but we don't remove request yet (maybe moving towards it)
            return False

        # Handle Consumption (Item)
        item_stats = world.get_component(target_id, ItemStats)
        if item_stats:
            if self.hunger_system:
                return self.hunger_system.process_consumption(
                    world, entity, request, transform, stats, target_id, item_stats
                )
            else:
                logger.warning(
                    "HungerSystem not available to handle consumption request."
                )
                return False

        # Handle Social Interaction (Talk/Fight/Dance)
        if request.action in ["Talk", "Fight", "Dance", "Greet"]:
            if self.social_system:
                self.social_system.process_interaction_request(world, entity, request)
                return True
            else:
                logger.warning("SocialSystem not available to handle social request.")
                return False

        # Handle Interaction with another Yukkuri (Predation)
        target_stats = world.get_component(target_id, YukkuriStats)
        if target_stats and request.consume:
            if self._check_predation_allowed(world, entity):
                # Execute Predation
                needs = world.get_component(entity, Needs)
                if needs:
                    needs.hunger = max(0, needs.hunger - 50.0)  # Big meal
                if self.audio:
                    self.audio.play_sound("eat")  # Crunch?

                world.destroy_entity(target_id)
                ai = world.get_component(entity, AIState)
                if ai and ai.current_target_id == target_id:
                    from typing import cast
                    from ...engine.types import EntityID
                    ai.current_target_id = cast(EntityID, -1)
                logger.info(f"Entity {entity} ate Yukkuri {target_id} (Predation).")
            else:
                logger.debug(
                    f"Entity {entity} attempted to eat Yukkuri {target_id} but lacks permission/trait."
                )

            # Predation request (valid or permission-failed) is considered handled by this system
            return True

        return False
