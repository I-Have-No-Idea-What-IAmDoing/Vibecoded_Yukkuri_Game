import json
import os
from typing import Any, Dict, TYPE_CHECKING, Optional
from loguru import logger
from ..engine.ecs import World
from .components import Transform, Sprite
from .yukkuri_components import YukkuriStats, ItemStats
from .player_components import PlayerState
from .systems.persistence_system import PersistenceSystem

if TYPE_CHECKING:
    from .entity_factory import EntityFactory

class GameManager:
    """
    Manages high-level game logic.

    Responsibilities:
    - Initializing the game world (creating player entity).
    - Providing high-level methods for game actions (like selling yukkuri).
    - Delegating save/load to PersistenceSystem.
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

        # Create Player Entity if it doesn't exist
        if not self.world.get_components(PlayerState):
            player = self.world.create_entity()
            self.world.add_component(player, PlayerState())
            logger.info(f"Created Player entity {player}")

    def _get_player_state(self) -> PlayerState:
        """Helper to get the player state component."""
        player_entities = self.world.get_components(PlayerState)
        if player_entities:
            return next(iter(player_entities.values()))

        # Fallback (should not happen if initialized correctly)
        # But creating one on the fly to avoid crashes
        player = self.world.create_entity()
        state = PlayerState()
        self.world.add_component(player, state)
        return state

    @property
    def money(self) -> int:
        """Gets the player's money from PlayerState."""
        return self._get_player_state().money

    @money.setter
    def money(self, value: int) -> None:
        """Sets the player's money in PlayerState."""
        self._get_player_state().money = value

    @property
    def time_elapsed(self) -> float:
        """Gets the elapsed time from PlayerState."""
        return self._get_player_state().time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        """Sets the elapsed time in PlayerState."""
        self._get_player_state().time_elapsed = value

    @property
    def save_dir(self) -> str:
         return self._get_player_state().save_dir

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
            self.money += value # Use property
            logger.info(f"Sold {stats.name} for {value}. Total Money: {self.money}")
            self.world.destroy_entity(entity)
            return value
        return 0

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Delegates saving to PersistenceSystem.
        """
        persistence = PersistenceSystem()
        persistence.ecs_world = self.world
        persistence.save(filename)

    def load_game(self, filename: str = "savegame.json") -> bool:
        """
        Delegates loading to PersistenceSystem.
        """
        persistence = PersistenceSystem()
        persistence.ecs_world = self.world
        return persistence.load(filename)
