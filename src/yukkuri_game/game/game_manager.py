import json
import os
from typing import Any, Dict, TYPE_CHECKING
from loguru import logger
from ..engine.ecs import World
from ..engine.event_bus import EventBus
from .components import Transform, Sprite
from .yukkuri_components import YukkuriStats, ItemStats
from .services import EconomyService, PersistenceService, TimeService
from .events import TrainEntityRequest, SellEntityRequest

if TYPE_CHECKING:
    from .entity_factory import EntityFactory

class GameManager:
    """
    Manages high-level game logic.
    Economy and time logic are delegated to services.

    Attributes:
        world (World): The ECS World instance.
        factory (EntityFactory): The factory used to recreate entities during load.
    """

    def __init__(self, world: World):
        """
        Initializes the GameManager.

        Args:
            world (World): The ECS World instance.
        """
        self.world = world
        from .entity_factory import EntityFactory
        self.factory = world.services.get(EntityFactory)

        self.event_bus = world.services.get(EventBus)
        if self.event_bus:
            self.event_bus.subscribe(TrainEntityRequest, self.on_train_entity)
            self.event_bus.subscribe(SellEntityRequest, self.on_sell_entity)

    @property
    def time_elapsed(self) -> float:
        """
        Gets the total elapsed game time.

        Returns:
            float: The time elapsed in seconds.
        """
        ts = self.world.services.try_get(TimeService)
        return ts.time_elapsed if ts else 0.0

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        """
        Sets the total elapsed game time.

        Args:
            value (float): The new time elapsed in seconds.
        """
        ts = self.world.services.try_get(TimeService)
        if ts:
            ts.time_elapsed = value

    @property
    def money(self) -> int:
        """
        Gets the current amount of money.

        Returns:
            int: The current money.
        """
        return self.world.services.get(EconomyService).get_money()

    @money.setter
    def money(self, value: int) -> None:
        """
        Sets the amount of money.

        Args:
            value (int): The new money amount.
        """
        self.world.services.get(EconomyService).set_money(value)

    def calculate_quality_score(self, yukkuri_stats: YukkuriStats) -> int:
        """
        Calculates the quality score (value) of a Yukkuri.

        Args:
            yukkuri_stats (YukkuriStats): The stats component of the Yukkuri.

        Returns:
            int: The calculated value in money.
        """
        # Base score
        score = 100.0

        # Happiness factor
        score += yukkuri_stats.happiness * 2

        # Badges
        score += yukkuri_stats.badges * 500

        # Health penalty
        if yukkuri_stats.health < yukkuri_stats.max_health:
            score -= (yukkuri_stats.max_health - yukkuri_stats.health) * 2

        # Age bonus
        score += int(yukkuri_stats.age / 60) * 10 # 10 points per minute alive

        yukkuri_stats.quality_score = score
        return int(score)

    def sell_yukkuri(self, entity: int) -> int:
        """
        Sells a Yukkuri entity.

        Calculates its value, adds to player money, and destroys the entity.

        Args:
            entity (int): The ID of the Yukkuri entity to sell.

        Returns:
            int: The amount of money gained, or 0 if the entity is not a Yukkuri.
        """
        stats = self.world.get_component(entity, YukkuriStats)
        if stats:
            value = self.calculate_quality_score(stats)
            economy = self.world.services.get(EconomyService)
            economy.add_money(value)
            logger.info(f"Sold {stats.name} for {value}. Total Money: {economy.get_money()}")
            self.world.destroy_entity(entity)
            return value
        return 0

    def on_sell_entity(self, event: SellEntityRequest) -> None:
        """
        Handles the SellEntityRequest event.

        Args:
            event (SellEntityRequest): The event containing the entity ID to sell.
        """
        self.sell_yukkuri(event.entity_id)

    def on_train_entity(self, event: TrainEntityRequest) -> None:
        """
        Handles the TrainEntityRequest event.

        Args:
            event (TrainEntityRequest): The event containing the entity ID to train.
        """
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            stats.badges += 1
            stats.happiness += 10
            logger.info(f"Trained entity {event.entity_id}. Badges: {stats.badges}")

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.
        Delegates to PersistenceService.

        Args:
            filename (str): The name of the save file. Defaults to "savegame.json".
        """
        persistence = self.world.services.try_get(PersistenceService)
        if persistence:
            persistence.save_game(filename)
        else:
            logger.error("PersistenceService not found.")


    def load_game(self, filename: str = "savegame.json") -> bool:
        """
        Loads a game state from a JSON file.
        Delegates to PersistenceService.

        Args:
            filename (str): The name of the save file. Defaults to "savegame.json".

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        persistence = self.world.services.try_get(PersistenceService)
        if persistence:
            return persistence.load_game(filename)
        else:
            logger.error("PersistenceService not found.")
            return False
