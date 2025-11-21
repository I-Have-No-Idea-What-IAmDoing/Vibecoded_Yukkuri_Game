import json
import os
from typing import Any, Dict, TYPE_CHECKING
from loguru import logger
from ..engine.ecs import World
from .components import Transform, Sprite
from .yukkuri_components import YukkuriStats, ItemStats
from .services import EconomyService, PersistenceService, TimeService

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
            world: The ECS World instance.
        """
        self.world = world
        from .entity_factory import EntityFactory
        self.factory = world.services.get(EntityFactory)

    @property
    def time_elapsed(self) -> float:
        """Legacy property to access time from TimeService."""
        ts = self.world.services.try_get(TimeService)
        return ts.time_elapsed if ts else 0.0

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        """Legacy setter to set time in TimeService."""
        ts = self.world.services.try_get(TimeService)
        if ts:
            ts.time_elapsed = value

    @property
    def money(self) -> int:
        """Legacy property to access money from EconomyService."""
        return self.world.services.get(EconomyService).get_money()

    @money.setter
    def money(self, value: int) -> None:
        """Legacy setter to set money in EconomyService."""
        self.world.services.get(EconomyService).set_money(value)

    def calculate_quality_score(self, yukkuri_stats: YukkuriStats) -> int:
        """
        Calculates the quality score (value) of a Yukkuri.

        Args:
            yukkuri_stats: The stats component of the Yukkuri.

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
            entity: The ID of the Yukkuri entity to sell.

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

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.
        Delegates to PersistenceService.

        Args:
            filename: The name of the save file. Defaults to "savegame.json".
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
            filename: The name of the save file. Defaults to "savegame.json".

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        persistence = self.world.services.try_get(PersistenceService)
        if persistence:
            return persistence.load_game(filename)
        else:
            logger.error("PersistenceService not found.")
            return False
