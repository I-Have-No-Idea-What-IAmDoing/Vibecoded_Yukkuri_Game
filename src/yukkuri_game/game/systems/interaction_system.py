import math
from loguru import logger
from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, ItemStats, AIState

class InteractionSystem(System):
    """
    System responsible for handling entity interactions (e.g. eating, sleeping).
    """
    def __init__(self):
        super().__init__()
        self.audio = None

    def update(self, world: World, dt: float) -> None:
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)

        # Get all entities with InteractionRequest
        # We need to iterate safely because we might remove components
        entities = list(world.get_components_tuple(InteractionRequest, Transform, YukkuriStats))

        for entity, (request, transform, stats) in entities:
            self._handle_interaction(world, entity, request, transform, stats)

            # Remove request after processing
            if world.has_component(entity, InteractionRequest):
                world.remove_component(entity, InteractionRequest)

    def _handle_interaction(self, world: World, entity: int, request: InteractionRequest,
                            transform: Transform, stats: YukkuriStats) -> None:
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

        item_stats = world.get_component(target_id, ItemStats)
        if item_stats:
            if item_stats.nutrition > 0:
                stats.hunger = max(0, stats.hunger - item_stats.nutrition)

            if item_stats.fun > 0:
                stats.happiness = min(100, stats.happiness + item_stats.fun)

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
