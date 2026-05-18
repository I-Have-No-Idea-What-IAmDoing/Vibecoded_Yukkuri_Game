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
from typing import cast

from loguru import logger

from ...engine.audio import AudioManager
from ...engine.ecs import System, World
from ...engine.types import EntityID
from ..components import (
    AIState,
    InteractionRequest,
    ItemStats,
    Needs,
    Personality,
    Predator,
    YukkuriStats,
)
from yukkuri_game.engine.components import (
    Transform,
)
from ..prefabs.effects import create_floating_text
from ..trait_service import TraitService
from .hunger_system import HungerSystem
from .social_system import SocialSystem


class InteractionSystem(System):
    """
    Routes InteractionRequests to specialized systems.

    Lazy-loads system references on first update to avoid
    circular dependencies during initialization.

    Attributes:
        audio (AudioManager | None): Audio manager.
        trait_service (TraitService | None): Trait service.
        hunger_system (HungerSystem | None): Hunger system.
        social_system (SocialSystem | None): Social system.
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
        personality = world.try_get_component(entity, Personality)
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

        target_transform = world.try_get_component(target_id, Transform)
        if not target_transform:
            return True

        # Range Check
        dist = math.hypot(
            transform.x - target_transform.x, transform.y - target_transform.y
        )
        if dist > 110.0:  # 110px threshold for movement jitter and physics.
            return False

        # Dispatch: Item Consumption
        item_stats = world.try_get_component(target_id, ItemStats)
        if item_stats:
            if self.hunger_system:
                return self.hunger_system.process_consumption(
                    world, entity, request, transform, target_id, item_stats
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
        target_stats = world.try_get_component(target_id, YukkuriStats)
        if target_stats and request.consume:
            return self._handle_predation(
                world, entity, target_id, stats, target_stats, target_transform
            )

        return False

    def _handle_predation(
        self,
        world: World,
        predator_id: int,
        prey_id: int,
        predator_stats: YukkuriStats,
        prey_stats: YukkuriStats,
        prey_transform: Transform,
    ) -> bool:
        """
        Handles the complexity of one Yukkuri eating another (Predation).

        Args:
            world: The ECS World.
            predator_id: ID of the attacker.
            prey_id: ID of the victim.
            predator_stats: Stats of the attacker.
            prey_stats: Stats of the victim.
            prey_transform: Transform of the victim (for floating text).

        Returns:
            bool: True (always handled, whether successful or not).
        """
        # 1. Agility Check / Dodge
        # If prey is significantly faster, they can dodge.
        if prey_stats.agility > predator_stats.agility * 1.5:
            logger.info(f"Yukkuri {prey_id} dodged predation from {predator_id}!")
            create_floating_text(
                world,
                prey_transform.x,
                prey_transform.y - 20,
                "Miss!",
                (255, 50, 50),
                size=24,
            )
            return True

        # 2. Permission Check
        if self._check_predation_allowed(world, predator_id):
            # 3. Execute Predation
            needs = world.try_get_component(predator_id, Needs)
            if needs:
                needs.adjust_hunger(-50.0)  # Big meal

            if self.audio:
                self.audio.play_sound("eat")

            world.destroy_entity(prey_id)

            # Clear AI Target if it fits
            ai = world.try_get_component(predator_id, AIState)
            if ai and ai.current_target_id == prey_id:
                ai.current_target_id = cast(EntityID, -1)

            logger.info(f"Entity {predator_id} ate Yukkuri {prey_id} (Predation).")
        else:
            logger.debug(
                f"Entity {predator_id} attempted to eat Yukkuri {prey_id} but lacks permission/trait."
            )

        return True
