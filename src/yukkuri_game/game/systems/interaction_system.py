from typing import Optional
from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..components import InteractionRequest, Transform
from ..yukkuri_components import YukkuriStats, ItemStats, AIState

class InteractionSystem(System):
    """
    System responsible for processing interaction requests (e.g. eating, sleeping).
    It moves logic that was previously in GameService.interact_with_item.
    """
    def __init__(self):
        self.audio: Optional[AudioManager] = None

    def update(self, world: World, dt: float) -> None:
        """
        Processes entities with InteractionRequest components.
        """
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)

        # Process all entities with InteractionRequest
        # Note: We iterate over a copy or collect them first because we will modify components/entities
        entities_to_process = []
        # Assuming world.get_entities_with returns IDs.

        for entity in world.get_entities_with(InteractionRequest):
            entities_to_process.append(entity)

        for entity in entities_to_process:
            request = world.get_component(entity, InteractionRequest)
            if request:
                self._process_interaction(world, entity, request)
                # Remove the request component after processing
                world.remove_component(entity, InteractionRequest)

    def _process_interaction(self, world: World, consumer_id: int, request: InteractionRequest) -> None:
        """
        Executes the interaction logic.
        """
        target_id = request.target_id
        consume = request.consume

        if not world.entity_exists(consumer_id) or not world.entity_exists(target_id):
            return

        item_stats = world.get_component(target_id, ItemStats)
        yukkuri_stats = world.get_component(consumer_id, YukkuriStats)

        if item_stats and yukkuri_stats:
            # Apply stats
            if item_stats.nutrition > 0:
                yukkuri_stats.hunger = max(0, yukkuri_stats.hunger - item_stats.nutrition)

            if item_stats.fun > 0:
                yukkuri_stats.happiness = min(100, yukkuri_stats.happiness + item_stats.fun)

            if item_stats.comfort > 0:
                yukkuri_stats.energy = min(100, yukkuri_stats.energy + item_stats.comfort)

            # Play sound
            if consume:
                if self.audio:
                    self.audio.play_sound("eat")

                # Destroy the item
                world.destroy_entity(target_id)

                # Clean up components that might linger if delayed destruction (defensive)
                if world.has_component(target_id, Transform):
                    world.remove_component(target_id, Transform)

                # Update consumer AI state if needed (e.g. reset target)
                ai = world.get_component(consumer_id, AIState)
                if ai and ai.current_target_id == target_id:
                    ai.current_target_id = -1
            else:
                # Non-consuming interaction (e.g. sleeping in bed, playing with permanent toy)
                # We might want to play a different sound depending on interaction type
                # But for now, logic is simple.
                pass
