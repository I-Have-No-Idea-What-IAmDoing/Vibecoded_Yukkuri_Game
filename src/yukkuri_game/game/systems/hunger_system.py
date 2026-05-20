"""
Hunger System - Food Consumption and Metabolism.

Processes item consumption requests dispatched from InteractionSystem.
Applies nutritional effects and handles item destruction.

Metabolism Effects:
-   Nutrition: Reduces hunger stat (hunger = need to eat).
-   Fun: Increases happiness (tasty food makes them happy).
-   Comfort: Restores energy (filling food makes them sleepy/content).
-   Waste Generation: Nutrition increases bladder at 50% rate.

Skill Integration:
-   Awards Scavenging XP when consuming items.
-   XP gain is flat rate (5.0 per item consumed).
"""

import math
from typing import cast

from yukkuri_game.engine.protocols import IAudioProvider
from ...engine.ecs import System, World
from ...engine.types import EntityID
from ..components import (
    AIState,
    EmotionalState,
    InteractionRequest,
    ItemStats,
    Needs,
    YukkuriStats,
)
from yukkuri_game.engine.components import (
    Transform,
)
from ..skill_constants import SkillId
from ..skill_service import SkillService


class HungerSystem(System):
    """
    Processes food consumption and applies metabolic effects.

    Lazy-loads AudioManager and SkillService on first update.
    Consumption requests are dispatched here from InteractionSystem.

    Attributes:
        audio (IAudioProvider | None): Audio manager for sound effects.
        skill_service (SkillService | None): Service for skill progression.
    """

    def __init__(self) -> None:
        """Initializes the HungerSystem."""
        super().__init__()
        self.audio: IAudioProvider | None = None
        self.skill_service: SkillService | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the hunger system.

        Note: Consumption logic is now dispatched from InteractionSystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.audio is None:
            self.audio = world.services.try_get(IAudioProvider)
        if self.skill_service is None:
            self.skill_service = world.services.try_get(SkillService)

    def process_consumption(
        self,
        world: World,
        consumer_id: int,
        request: InteractionRequest,
        consumer_transform: Transform,
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
            item_id (int): The entity ID of the item being consumed.
            item_stats (ItemStats): Stats of the item.

        Returns:
            bool: True if consumption was processed (valid), False otherwise.
        """
        # Ensure services are loaded — process_consumption may be called
        # via cross-system dispatch before update() has had a chance to run.
        if self.audio is None:
            self.audio = world.services.try_get(IAudioProvider)
        if self.skill_service is None:
            self.skill_service = world.services.try_get(SkillService)

        consumer_needs = world.try_get_component(consumer_id, Needs)
        if not consumer_needs:
            # Cannot eat if no needs component (weird but possible if malformed)
            return False

        target_transform = world.try_get_component(item_id, Transform)
        if not target_transform:
            return False

        # Verify distance
        dist = math.hypot(
            consumer_transform.x - target_transform.x,
            consumer_transform.y - target_transform.y,
        )
        if dist > 110.0:
            return False

        # Stat Effects
        emotional = world.try_get_component(consumer_id, EmotionalState)
        
        # Fun/Happiness from food consumption is processed separately
        # under metabolism to account for spoiled tastebuds. Play or
        # non-metabolic fun uses the standard adjustment.
        is_food_consumption = request.consume and item_stats.nutrition > 0
        if item_stats.fun > 0 and emotional and not is_food_consumption:
            emotional.adjust_happiness(item_stats.fun)

        # Nutritional/Metabolic effects ONLY if consumed
        if request.consume:
            # Apply nutrition: decreases hunger (lower = less hungry)
            if item_stats.nutrition > 0:
                initial_hunger = consumer_needs.hunger
                consumer_needs.adjust_hunger(-item_stats.nutrition)
                # Waste generation: food creates biological waste at 50% rate
                consumer_needs.adjust_bladder(item_stats.nutrition * 0.5)

                # Process spoiled tastebuds pickiness and happiness adjustments
                ystats = world.try_get_component(consumer_id, YukkuriStats)
                fun_gain = item_stats.fun
                if (
                    ystats
                    and ystats.tastebud_spoiled > 0.0
                    and item_stats.quality < ystats.tastebud_spoiled
                ):
                    base_mult = max(
                        0.0,
                        min(
                            1.0,
                            item_stats.quality / ystats.tastebud_spoiled
                        )
                    )
                    # Hunger bypass logic (Approach C)
                    hunger = initial_hunger
                    if hunger >= 50.0:
                        hunger_factor = max(
                            0.0,
                            min(1.0, (hunger - 50.0) / 30.0)
                        )
                        multiplier = (
                            base_mult
                            + (1.0 - base_mult) * hunger_factor
                        )
                    else:
                        multiplier = base_mult
                    
                    fun_gain = item_stats.fun * multiplier
                    
                    # Create floating feedback if significantly penalized
                    if multiplier < 0.99 and item_stats.fun > 0:
                        from ..prefabs.effects import create_floating_text
                        trans = world.try_get_component(consumer_id, Transform)
                        if trans:
                            create_floating_text(
                                world,
                                trans.x,
                                trans.y - 20,
                                f"Tastes bland... (+{int(fun_gain)} Happy)",
                                (200, 150, 150),
                                size=20,
                            )
                
                if fun_gain > 0 and emotional:
                    emotional.adjust_happiness(fun_gain)

                # Update tastebud spoiled standard after evaluating
                # current meal happiness
                if ystats:
                    ystats.tastebud_spoiled = max(
                        ystats.tastebud_spoiled,
                        item_stats.quality
                    )

            # Comfort foods restore energy (filling, warm foods)
            if item_stats.comfort > 0:
                consumer_needs.adjust_energy(item_stats.comfort)

            # Award scavenging XP only for eating
            if self.skill_service:
                self.skill_service.add_xp(consumer_id, SkillId.SCAVENGING, 5.0)

        # Item Destruction
        if request.consume:
            if self.audio:
                self.audio.play_sound("eat")

            # Remove item from world (consumed)
            world.commands.destroy_entity(item_id)

            # Clear AI target reference to prevent stale target pursuit
            ai = world.try_get_component(consumer_id, AIState)
            if ai and ai.current_target_id == item_id:
                ai.current_target_id = cast(EntityID, -1)

        return True
