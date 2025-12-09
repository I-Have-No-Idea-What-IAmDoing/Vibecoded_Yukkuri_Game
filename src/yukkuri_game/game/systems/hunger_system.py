"""
Module defining the HungerSystem for handling food consumption and metabolism.
"""

import math
from typing import Optional

from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, Needs, ItemStats, AIState, EmotionalState
from ..skill_service import SkillService
from ..skill_constants import SkillId


class HungerSystem(System):
    """
    System responsible for processing consumption interactions (eating items).
    """

    def __init__(self) -> None:
        super().__init__()
        self.audio: Optional[AudioManager] = None
        self.skill_service: Optional[SkillService] = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the hunger system.
        Note: Consumption logic is now dispatched from InteractionSystem.
        """
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)
        if self.skill_service is None:
            self.skill_service = world.services.try_get(SkillService)

    def process_consumption(
        self,
        world: World,
        consumer_id: int,
        request: InteractionRequest,
        consumer_transform: Transform,
        consumer_stats: YukkuriStats,
        item_id: int,
        item_stats: ItemStats,
    ) -> bool:
        """
        Executes the logic for eating an item.

        Returns:
            bool: True if consumption was processed (valid).
        """
        # Ensure services are loaded
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)
        if self.skill_service is None:
            self.skill_service = world.services.try_get(SkillService)

        consumer_needs = world.get_component(consumer_id, Needs)
        if not consumer_needs:
            # Cannot eat if no needs component (weird but possible if malformed)
            return False

        target_transform = world.get_component(item_id, Transform)
        if not target_transform:
            return False

        # Verify distance
        dist = math.hypot(
            consumer_transform.x - target_transform.x,
            consumer_transform.y - target_transform.y,
        )
        if dist > 50.0:
            return False

        # Apply Stats
        if item_stats.nutrition > 0:
            consumer_needs.hunger = max(0, consumer_needs.hunger - item_stats.nutrition)
            # Increase bladder (waste) based on nutrition consumed.
            # Using 0.5 as a conversion factor (20 nutrition -> 10 waste).
            consumer_needs.bladder = min(
                100, consumer_needs.bladder + (item_stats.nutrition * 0.5)
            )

        emotional = world.get_component(consumer_id, EmotionalState)
        if item_stats.fun > 0 and emotional:
            emotional.happiness = min(100, emotional.happiness + item_stats.fun)

        if item_stats.comfort > 0:
            consumer_needs.energy = min(100, consumer_needs.energy + item_stats.comfort)

        # Apply Scavenging XP
        if self.skill_service:
            self.skill_service.add_xp(consumer_id, SkillId.SCAVENGING, 5.0)

        # Consume Item
        if request.consume:
            if self.audio:
                self.audio.play_sound("eat")

            world.destroy_entity(item_id)
            if world.has_component(item_id, Transform):
                world.remove_component(item_id, Transform)

            ai = world.get_component(consumer_id, AIState)
            if ai and ai.current_target_id == item_id:
                ai.current_target_id = -1

        return True
