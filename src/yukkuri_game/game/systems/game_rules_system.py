"""
Game Rules System - Player Action Handlers.

Processes player commands for entity management:
- Sell: Convert Yukkuri to currency, value based on stats/health/happiness
- Train: Award badges and boost happiness (reward-based training)
- Punish: Reduce health/happiness, increase stress/discipline

Event-Driven Architecture:
- Subscribes to request events (SellEntityRequest, TrainEntityRequest, etc.)
- Publishes result events (EntitySoldEvent, EntityTrainedEvent, etc.)
- UI systems listen to result events for feedback (floating text, sounds)

Game Balance Notes:
- Selling value scales with entity condition (healthy/happy = more valuable)
- Training adds +1 badge, +10 happiness
- Punishment deals -10 health, -20 happiness, +20 stress, +10 discipline
"""

from loguru import logger

from ...engine.protocols import IAudioProvider
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import (
    EmotionalState,
    Needs,
    YukkuriStats,
)
from ...engine.components import (
    Transform,
)
from ..events import (
    EntityPunishedEvent,
    EntitySoldEvent,
    EntityTrainedEvent,
    PunishEntityRequest,
    SellEntityRequest,
    TrainEntityRequest,
)
from ..services import EconomyService


class GameRulesSystem(System):
    """
    Event-driven system for player management actions.

    Purely event-driven: update() is a no-op. All logic triggered
    by event subscriptions established in __init__.
    """

    def __init__(self) -> None:
        """
        Initializes the GameRulesSystem.
        """
        self.event_bus: EventBus

    def initialize(self) -> None:
        """
        Captures world reference on registration and subscribes to events.
        """
        self.event_bus = self.ecs_world.services.get(EventBus)

        self.event_bus.subscribe(TrainEntityRequest, self.on_train_entity)
        self.event_bus.subscribe(PunishEntityRequest, self.on_punish_entity)
        self.event_bus.subscribe(SellEntityRequest, self.on_sell_entity)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system.
        This system is primarily event-driven; update() is a no-op.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """

    def sell_yukkuri(self, entity: int) -> int:
        """
        Sells a Yukkuri entity and destroys it.

        Args:
            entity (int): The ID of the entity to sell.

        Returns:
            int: The value the entity was sold for.
        """
        world = self.ecs_world

        stats = world.try_get_component(entity, YukkuriStats)
        needs = world.try_get_component(entity, Needs)
        emotional_state = world.try_get_component(entity, EmotionalState)

        if stats:
            from ...config import GameConfig

            config = self.ecs_world.services.try_get(GameConfig)
            stats_config = config.rules.stats if config else None

            # Calculate sale value based on current condition:
            # - Base value from stats (badges, age, type rarity)
            # - Modifiers from health, happiness, traits
            # - Minimum value is 0 (worthless but still removable)
            value = max(
                0,
                stats.calculate_value(
                    needs, emotional_state, stats_config=stats_config
                ),
            )

            # Credit player account
            economy = self.ecs_world.services.get(EconomyService)
            economy.add_money(value)
            logger.info(
                f"Sold {stats.name} for {value}. Total Money: {economy.money}"
            )

            # Get position for visual feedback spawn point
            transform = self.ecs_world.try_get_component(entity, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            # Audio/visual feedback
            audio = self.ecs_world.services.try_get(IAudioProvider)
            if audio:
                audio.play_sound("sell")

            # Notify listeners (for floating text, achievements, etc.)
            self.event_bus.publish(EntitySoldEvent(entity, value, position))
            self.ecs_world.commands.destroy_entity(entity)
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
        stats = self.ecs_world.try_get_component(event.entity_id, YukkuriStats)
        emotional_state = self.ecs_world.try_get_component(event.entity_id, EmotionalState)
        if stats:
            # Award training badge (increases sell value and prestige)
            stats.badges += 1

            # Positive reinforcement: training makes them happier
            if emotional_state:
                emotional_state.adjust_happiness(10.0)

            transform = self.ecs_world.try_get_component(event.entity_id, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            audio = self.ecs_world.services.try_get(IAudioProvider)
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
        stats = self.ecs_world.try_get_component(event.entity_id, YukkuriStats)
        needs = self.ecs_world.try_get_component(event.entity_id, Needs)
        emotional_state = self.ecs_world.try_get_component(event.entity_id, EmotionalState)

        if stats and needs:
            # Physical damage from punishment
            needs.adjust_health(-10.0)

            if emotional_state:
                # Emotional harm: less happy, more stressed
                emotional_state.adjust_happiness(-20.0)
                emotional_state.adjust_stress(20.0)

            # Discipline increase: punishment teaches obedience
            # Higher discipline = less likely to misbehave, but also less happy baseline
            stats.discipline = min(100.0, stats.discipline + 10.0)

            transform = self.ecs_world.try_get_component(event.entity_id, Transform)
            position = (transform.x, transform.y) if transform else (0, 0)

            audio = self.ecs_world.services.try_get(IAudioProvider)
            if audio:
                audio.play_sound("hit")

            self.event_bus.publish(EntityPunishedEvent(event.entity_id, position))
            logger.info(
                f"Punished entity {event.entity_id}. Health: {needs.health}, Discipline: {stats.discipline}"
            )
