import json
import os
from loguru import logger
from ..engine.ecs import World
from .components import Transform, Sprite
from .yukkuri_components import YukkuriStats, ItemStats

class GameManager:
    def __init__(self, world: World, entity_factory):
        self.world = world
        self.factory = entity_factory
        self.money = 1000
        self.time_elapsed = 0.0
        self.save_dir = "saves"

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def calculate_quality_score(self, yukkuri_stats: YukkuriStats) -> int:
        # Base score
        score = 100

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

    def sell_yukkuri(self, entity: int):
        stats = self.world.get_component(entity, YukkuriStats)
        if stats:
            value = self.calculate_quality_score(stats)
            self.money += value
            logger.info(f"Sold {stats.name} for {value}. Total Money: {self.money}")
            self.world.destroy_entity(entity)
            return value
        return 0

    def save_game(self, filename="savegame.json"):
        data = {
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
            ent_data = {}

            # Transform
            trans = self.world.get_component(entity, Transform)
            if trans:
                ent_data["transform"] = {"x": trans.x, "y": trans.y}

            # Yukkuri Stats
            y_stats = self.world.get_component(entity, YukkuriStats)
            if y_stats:
                ent_data["yukkuri"] = {
                    "type_id": y_stats.type_id,
                    "name": y_stats.name,
                    "health": y_stats.health,
                    "hunger": y_stats.hunger,
                    "happiness": y_stats.happiness,
                    "badges": y_stats.badges,
                    "age": y_stats.age
                }

            # Item Stats
            i_stats = self.world.get_component(entity, ItemStats)
            if i_stats:
                ent_data["item"] = {
                    "type_id": i_stats.type_id
                }

            if "yukkuri" in ent_data or "item" in ent_data:
                data["entities"].append(ent_data)

        path = os.path.join(self.save_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Game saved to {path}")

    def load_game(self, filename="savegame.json"):
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
            x, y = trans["x"], trans["y"]

            if "yukkuri" in ent_data:
                y_data = ent_data["yukkuri"]
                eid = self.factory.create_yukkuri(y_data["type_id"], x, y)
                stats = self.world.get_component(eid, YukkuriStats)
                stats.name = y_data["name"]
                stats.health = y_data["health"]
                stats.hunger = y_data["hunger"]
                stats.happiness = y_data["happiness"]
                stats.badges = y_data["badges"]
                stats.age = y_data["age"]

            elif "item" in ent_data:
                i_data = ent_data["item"]
                self.factory.create_item(i_data["type_id"], x, y)

        logger.info("Game loaded.")
        return True
