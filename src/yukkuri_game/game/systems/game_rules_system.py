"""
Game Rules System.
Handles high-level game logic like selling, training, and punishing entities.
"""
from loguru import logger
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..components import Transform
from ..yukkuri_components import YukkuriStats, EmotionalState
from ..services import EconomyService
from ..events import (
    TrainEntityRequest,
    PunishEntityRequest,
    SellEntityRequest,
    EntitySoldEvent,
    EntityTrainedEvent,
    EntityPunishedEvent
)

class GameRulesSystem(System):
    """
    System that enforces game rules and handles player actions like selling/training.
    """
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe(TrainEntityRequest, self.on_train_entity)
        self.event_bus.subscribe(PunishEntityRequest, self.on_punish_entity)
        self.event_bus.subscribe(SellEntityRequest, self.on_sell_entity)
        self.ecs_world: World = None # Injected by World.add_system

    def update(self, world: World, dt: float) -> None:
        # This system is event-driven, so update loop might not be needed
        # unless we want to process a queue. For now, immediate handlers are fine
        # as per previous implementation (GameManager was not a System but had handlers).
        pass

    def sell_yukkuri(self, entity: int) -> int:
        stats = self.ecs_world.get_component(entity, YukkuriStats)
        emotional_state = self.ecs_world.get_component(entity, EmotionalState)
        if stats:
            value = max(0, stats.calculate_value(emotional_state))
            economy = self.ecs_world.services.get(EconomyService)
            economy.add_money(value)
            logger.info(f"Sold {stats.name} for {value}. Total Money: {economy.get_money()}")

            transform = self.ecs_world.get_component(entity, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            audio = self.ecs_world.services.try_get(AudioManager)
            if audio:
                audio.play_sound("sell")

            self.event_bus.publish(EntitySoldEvent(entity, value, position))
            self.ecs_world.destroy_entity(entity)
            return value
        return 0

    def on_sell_entity(self, event: SellEntityRequest) -> None:
        self.sell_yukkuri(event.entity_id)

    def on_train_entity(self, event: TrainEntityRequest) -> None:
        stats = self.ecs_world.get_component(event.entity_id, YukkuriStats)
        emotional_state = self.ecs_world.get_component(event.entity_id, EmotionalState)
        if stats:
            stats.badges += 1
            if emotional_state:
                emotional_state.happiness = min(100.0, emotional_state.happiness + 10.0)

            transform = self.ecs_world.get_component(event.entity_id, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            audio = self.ecs_world.services.try_get(AudioManager)
            if audio:
                audio.play_sound("train")

            self.event_bus.publish(EntityTrainedEvent(event.entity_id, position))
            logger.info(f"Trained entity {event.entity_id}. Badges: {stats.badges}")

    def on_punish_entity(self, event: PunishEntityRequest) -> None:
        stats = self.ecs_world.get_component(event.entity_id, YukkuriStats)
        emotional_state = self.ecs_world.get_component(event.entity_id, EmotionalState)
        if stats:
            stats.health = max(0.0, stats.health - 10.0)
            if emotional_state:
                emotional_state.happiness = max(-100.0, emotional_state.happiness - 20.0)
                emotional_state.stress = min(100.0, emotional_state.stress + 20.0)

            stats.discipline = min(100.0, stats.discipline + 10.0)

            transform = self.ecs_world.get_component(event.entity_id, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            audio = self.ecs_world.services.try_get(AudioManager)
            if audio:
                audio.play_sound("hit")

            self.event_bus.publish(EntityPunishedEvent(event.entity_id, position))
            logger.info(f"Punished entity {event.entity_id}. Health: {stats.health}, Discipline: {stats.discipline}")
