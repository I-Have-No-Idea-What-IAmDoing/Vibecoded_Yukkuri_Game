"""
Game Rules System.
Handles high-level game logic like selling, training, and punishing entities.
"""
from typing import Optional
from loguru import logger
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..components import Transform
from ..yukkuri_components import YukkuriStats, Needs, EmotionalState
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

    Attributes:
        event_bus (EventBus): The event bus for subscription and publishing.
        ecs_world (World): The ECS World instance (injected).
    """
    def __init__(self, event_bus: EventBus):
        """
        Initializes the GameRulesSystem.

        Args:
            event_bus (EventBus): The event bus instance.
        """
        self.event_bus = event_bus
        self.event_bus.subscribe(TrainEntityRequest, self.on_train_entity)
        self.event_bus.subscribe(PunishEntityRequest, self.on_punish_entity)
        self.event_bus.subscribe(SellEntityRequest, self.on_sell_entity)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system.
        This system is primarily event-driven, so this is a no-op.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        # This system is event-driven
        pass

    def sell_yukkuri(self, entity: int) -> int:
        """
        Sells a Yukkuri entity and destroys it.

        Args:
            entity (int): The ID of the entity to sell.

        Returns:
            int: The value the entity was sold for.
        """
        if not hasattr(self, 'ecs_world'):
             logger.error("GameRulesSystem: ecs_world not injected.")
             return 0

        stats = self.ecs_world.get_component(entity, YukkuriStats)
        needs = self.ecs_world.get_component(entity, Needs)
        emotional_state = self.ecs_world.get_component(entity, EmotionalState)

        if stats:
            # Get Config
            from ...config import GameConfig
            config = self.ecs_world.services.try_get(GameConfig)
            stats_config = config.rules.stats if config else None

            # Assuming calculate_value now takes needs
            value = max(0, stats.calculate_value(needs, emotional_state, stats_config=stats_config))
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
        """
        Handles the SellEntityRequest event.

        Args:
            event (SellEntityRequest): The event data.

        Returns:
            None
        """
        self.sell_yukkuri(event.entity_id)

    def on_train_entity(self, event: TrainEntityRequest) -> None:
        """
        Handles the TrainEntityRequest event.
        Increases badges and happiness.

        Args:
            event (TrainEntityRequest): The event data.

        Returns:
            None
        """
        if not hasattr(self, 'ecs_world'): return

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
        """
        Handles the PunishEntityRequest event.
        Decreases health/happiness, increases stress/discipline.

        Args:
            event (PunishEntityRequest): The event data.

        Returns:
            None
        """
        if not hasattr(self, 'ecs_world'): return

        stats = self.ecs_world.get_component(event.entity_id, YukkuriStats)
        needs = self.ecs_world.get_component(event.entity_id, Needs)
        emotional_state = self.ecs_world.get_component(event.entity_id, EmotionalState)

        if stats and needs:
            needs.health = max(0.0, needs.health - 10.0)
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
            logger.info(f"Punished entity {event.entity_id}. Health: {needs.health}, Discipline: {stats.discipline}")
