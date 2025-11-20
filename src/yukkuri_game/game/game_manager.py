import json
import os
from typing import Any, Dict
from loguru import logger
from ..engine.ecs import World
from .components import Transform, Sprite
from .yukkuri_components import YukkuriStats, ItemStats

class GameManager:
    """
    Manages high-level game logic, including economy, time, and save/load functionality.

    Attributes:
        world (World): The ECS World instance.
        factory (EntityFactory): The factory used to recreate entities during load.
        money (int): The player's current money.
        time_elapsed (float): Total game time elapsed in seconds.
        save_dir (str): Directory where save files are stored.
    """

    def __init__(self, world: World, entity_factory):
        """
        Initializes the GameManager.

        Args:
            world: The ECS World instance.
            entity_factory: The EntityFactory instance.
        """
        self.world = world
        self.factory = entity_factory
        self.money = 1000
        self.time_elapsed = 0.0
        self.save_dir = "saves"

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

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
            self.money += value
            logger.info(f"Sold {stats.name} for {value}. Total Money: {self.money}")
            self.world.destroy_entity(entity)
            return value
        return 0

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.

        Args:
            filename: The name of the save file. Defaults to "savegame.json".
        """
        data: dict[str, int | float | list] = {
            "money": self.money,
            "time": self.time_elapsed,
            "entities": []
        }

        # Serialize Entities
        # We need to iterate all entities and save their components
        # For MVP, we only care about Yukkuri and Items with Transforms and Stats

        # Get all entities
        # This is a bit tricky in our simple ECS as we don't have a list of all entities readily available
        # except via internal list.

        for entity in self.world._entities:
            ent_data: Dict[str, Any] = {}

            # Transform
            trans = self.world.get_component(entity, Transform)
            if trans:
                ent_data["transform"] = {"x": float(trans.x), "y": float(trans.y)}

            # Yukkuri Stats
            y_stats = self.world.get_component(entity, YukkuriStats)
            if y_stats:
                ent_data["yukkuri"] = {
                    "type_id": y_stats.type_id,
                    "name": y_stats.name,
                    "health": float(y_stats.health),
                    "hunger": float(y_stats.hunger),
                    "happiness": float(y_stats.happiness),
                    "badges": int(y_stats.badges),
                    "age": float(y_stats.age)
                }

            # Item Stats
            i_stats = self.world.get_component(entity, ItemStats)
            if i_stats:
                ent_data["item"] = {
                    "type_id": i_stats.type_id
                }
                # We can verify it conforms to expected structure, but simple assignment is fine for now
                # since mypy only complains if we try to put incompatible types into data["entities"] if it was typed more strictly.
                # The real issue is the previous dict items for ent_data being incompatible with a strict TypedDict if we were using one.
                # Since ent_data is just Dict[str, Any] effectively, it should be fine, but mypy inferred the dict type from first assignment.

            if "yukkuri" in ent_data or "item" in ent_data:
                 if isinstance(data["entities"], list):
                    data["entities"].append(ent_data)

        path = os.path.join(self.save_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Game saved to {path}")

    def load_game(self, filename: str = "savegame.json") -> bool:
        """
        Loads a game state from a JSON file.

        Clears the current world and recreates entities from the save data.

        Args:
            filename: The name of the save file. Defaults to "savegame.json".

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        path = os.path.join(self.save_dir, filename)
        if not os.path.exists(path):
            logger.warning("Save file not found.")
            return False

        with open(path, "r") as f:
            data = json.load(f)

        self.money = data.get("money", 1000)
        self.time_elapsed = data.get("time", 0)

        # Clear existing entities
        # In a real game we might want to reset the world properly
        # For MVP, we assume load is done at start or we clear manually.
        # Let's clear.
        for entity in list(self.world._entities):
            self.world.destroy_entity(entity)

        for ent_data in data.get("entities", []):
            trans = ent_data.get("transform")
            x, y = float(trans["x"]), float(trans["y"])

            if "yukkuri" in ent_data:
                y_data = ent_data["yukkuri"]
                eid = self.factory.create_yukkuri(y_data["type_id"], x, y)
                stats = self.world.get_component(eid, YukkuriStats)
                if stats:
                    stats.name = y_data["name"]
                    stats.health = float(y_data["health"])
                    stats.hunger = float(y_data["hunger"])
                    stats.happiness = float(y_data["happiness"])
                    stats.badges = int(y_data["badges"])
                    stats.age = float(y_data["age"])

            elif "item" in ent_data:
                i_data = ent_data["item"]
                self.factory.create_item(i_data["type_id"], x, y)

        logger.info("Game loaded.")
        return True
