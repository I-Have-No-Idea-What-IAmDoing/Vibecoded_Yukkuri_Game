"""
Module defining the HungerSystem for handling food consumption and metabolism.
"""
import math
from typing import Optional
from loguru import logger

from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, ItemStats, AIState, EmotionalState
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
        Updates the hunger system, processing consumption requests.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)
        if self.skill_service is None:
            self.skill_service = world.services.try_get(SkillService)

        # Get all entities with InteractionRequest
        entities = list(world.get_components_tuple(InteractionRequest, Transform, YukkuriStats))

        for entity, (request, transform, stats) in entities:
            target_id = request.target_id

            if not world.entity_exists(target_id):
                continue

            # Check if target is an item (has ItemStats)
            item_stats = world.get_component(target_id, ItemStats)
            if item_stats:
                # This is a consumption request
                self._process_consumption(world, entity, request, transform, stats, target_id, item_stats)

                # We processed this request, remove it so InteractionSystem doesn't try to use it
                # (Assuming InteractionSystem handles other types like social or predation on other yukkuris)
                if world.has_component(entity, InteractionRequest):
                    world.remove_component(entity, InteractionRequest)

    def _process_consumption(self, world: World, consumer_id: int, request: InteractionRequest,
                             consumer_transform: Transform, consumer_stats: YukkuriStats,
                             item_id: int, item_stats: ItemStats) -> None:
        """
        Executes the logic for eating an item.
        """
        target_transform = world.get_component(item_id, Transform)
        if not target_transform:
            return

        # Verify distance
        dist = math.hypot(consumer_transform.x - target_transform.x, consumer_transform.y - target_transform.y)
        if dist > 50.0:
            return

        # Apply Stats
        if item_stats.nutrition > 0:
            consumer_stats.hunger = max(0, consumer_stats.hunger - item_stats.nutrition)

        emotional = world.get_component(consumer_id, EmotionalState)
        if item_stats.fun > 0 and emotional:
            emotional.happiness = min(100, emotional.happiness + item_stats.fun)

        if item_stats.comfort > 0:
            consumer_stats.energy = min(100, consumer_stats.energy + item_stats.comfort)

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
