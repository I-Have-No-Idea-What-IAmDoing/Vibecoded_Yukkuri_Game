"""
Interaction System - Action Request Dispatcher.

Processes InteractionRequest components and routes them to appropriate handlers.
Acts as a central hub for entity-to-entity and entity-to-item interactions.

Interaction Types:
-   Item consumption: Routed to HungerSystem.
-   Social actions (Talk, Fight, Dance, Greet): Routed to SocialSystem.
-   Predation: Handled directly (eating other Yukkuris, requires permission).

Request Lifecycle:
1.  AI system adds InteractionRequest component to entity.
2.  This system processes request each frame.
3.  If within range, dispatches to appropriate handler.
4.  On success, removes the InteractionRequest component.
"""

import math
from typing import cast, Optional, List
from loguru import logger

from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ...engine.types import EntityID
from ..components import Transform, InteractionRequest
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    ItemStats,
    AIState,
    Personality,
    Predator,
)
from ..trait_service import TraitService
from .hunger_system import HungerSystem
from .social_system import SocialSystem


class InteractionSystem(System):
    """
    Routes InteractionRequests to specialized systems.

    Lazy-loads system references on first update to avoid
    circular dependencies during initialization.

    Attributes:
        audio (Optional[AudioManager]): Audio manager.
        trait_service (Optional[TraitService]): Trait service.
        hunger_system (Optional[HungerSystem]): Hunger system.
        social_system (Optional[SocialSystem]): Social system.
    """

    def __init__(self) -> None:
        """Initializes the InteractionSystem."""
        super().__init__()
        self.audio: Optional[AudioManager] = None
        self.trait_service: Optional[TraitService] = None
        self.hunger_system: Optional[HungerSystem] = None
        self.social_system: Optional[SocialSystem] = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the interaction system.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)
        if self.hunger_system is None:
            self.hunger_system = world.services.try_get(HungerSystem)
        if self.social_system is None:
            self.social_system = world.services.try_get(SocialSystem)

        # Process interaction requests (iterate copy for safe removal).
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

            if personality.cached_overrides and personality.cached_overrides.get(
                "can_eat_yukkuri", False
            ):
                return True

            if world.has_component(entity, Predator):
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

        # Validation
        if not world.entity_exists(target_id):
            return True

        target_transform = world.get_component(target_id, Transform)
        if not target_transform:
            return True

        # Range Check
        dist = math.hypot(
            transform.x - target_transform.x, transform.y - target_transform.y
        )
        if dist > 70.0:  # 70px threshold for movement jitter.
            return False

        # Dispatch: Item Consumption
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

        # Dispatch: Social Actions
        if request.action in ["Talk", "Fight", "Dance", "Greet"]:
            if self.social_system:
                self.social_system.process_interaction_request(world, entity, request)
                return True
            else:
                logger.warning("SocialSystem not available to handle social request.")
                return False

        # Dispatch: Predation
        # Special case: eating another Yukkuri (requires trait permission)
        target_stats = world.get_component(target_id, YukkuriStats)
        if target_stats and request.consume:
            if self._check_predation_allowed(world, entity):
                # Execute Predation
                needs = world.get_component(entity, Needs)
                if needs:
                    needs.hunger = max(0, needs.hunger - 50.0)  # Big meal
                if self.audio:
                    self.audio.play_sound("eat")

                world.destroy_entity(target_id)
                ai = world.get_component(entity, AIState)
                if ai and ai.current_target_id == target_id:
                    ai.current_target_id = cast(EntityID, -1)
                logger.info(f"Entity {entity} ate Yukkuri {target_id} (Predation).")
            else:
                logger.debug(
                    f"Entity {entity} attempted to eat Yukkuri {target_id} but lacks permission/trait."
                )

            # Predation request (valid or permission-failed) is considered handled by this system
            return True

        return False
