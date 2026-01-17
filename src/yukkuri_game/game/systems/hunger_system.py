"""
Hunger System - Food Consumption and Metabolism.

Processes item consumption requests dispatched from InteractionSystem.
Applies nutritional effects and handles item destruction.

Metabolism Effects:
- Nutrition: Reduces hunger stat (hunger = need to eat)
- Fun: Increases happiness (tasty food makes them happy)
- Comfort: Restores energy (filling food makes them sleepy/content)
- Waste Generation: Nutrition increases bladder at 50% rate

Skill Integration:
- Awards Scavenging XP when consuming items
- XP gain is flat rate (5.0 per item consumed)
"""

import math

from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ...engine.types import EntityID
from typing import cast
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, Needs, ItemStats, AIState, EmotionalState
from ..skill_service import SkillService
from ..skill_constants import SkillId


class HungerSystem(System):
    """
    Processes food consumption and applies metabolic effects.

    Lazy-loads AudioManager and SkillService on first update.
    Consumption requests are dispatched here from InteractionSystem.
    """

    def __init__(self) -> None:
        """Initializes the HungerSystem."""
        super().__init__()
        self.audio: AudioManager | None = None
        self.skill_service: SkillService | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the hunger system.
        Note: Consumption logic is now dispatched from InteractionSystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
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

        Args:
            world (World): The ECS World.
            consumer_id (int): The entity ID consuming the item.
            request (InteractionRequest): The interaction request details.
            consumer_transform (Transform): Transform of the consumer.
            consumer_stats (YukkuriStats): Stats of the consumer.
            item_id (int): The entity ID of the item being consumed.
            item_stats (ItemStats): Stats of the item.

        Returns:
            bool: True if consumption was processed (valid), False otherwise.
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

        # ==================== STAT EFFECTS ====================
        # Apply nutrition: decreases hunger (lower = less hungry)
        if item_stats.nutrition > 0:
            consumer_needs.hunger = max(0, consumer_needs.hunger - item_stats.nutrition)
            # Waste generation: food creates biological waste at 50% rate
            # e.g., 20 nutrition creates 10 bladder pressure
            consumer_needs.bladder = min(
                100, consumer_needs.bladder + (item_stats.nutrition * 0.5)
            )

        # Fun foods increase happiness (treats, sweets)
        emotional = world.get_component(consumer_id, EmotionalState)
        if item_stats.fun > 0 and emotional:
            emotional.happiness = min(100, emotional.happiness + item_stats.fun)

        # Comfort foods restore energy (filling, warm foods)
        if item_stats.comfort > 0:
            consumer_needs.energy = min(100, consumer_needs.energy + item_stats.comfort)

        # ==================== SKILL XP ====================
        # Award scavenging XP for finding and consuming food
        if self.skill_service:
            self.skill_service.add_xp(consumer_id, SkillId.SCAVENGING, 5.0)

        # ==================== ITEM DESTRUCTION ====================
        if request.consume:
            if self.audio:
                self.audio.play_sound("eat")

            # Remove item from world (consumed)
            world.destroy_entity(item_id)
            if world.has_component(item_id, Transform):
                world.remove_component(item_id, Transform)

            # Clear AI target reference to prevent stale target pursuit
            ai = world.get_component(consumer_id, AIState)
            if ai and ai.current_target_id == item_id:
                ai.current_target_id = cast(EntityID, -1)

        return True
