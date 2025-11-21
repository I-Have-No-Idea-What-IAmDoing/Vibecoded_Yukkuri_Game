import json
import os
from typing import Dict, Any, List, Type
from loguru import logger
from ...engine.ecs import World, System
from ..components import Transform, Sprite
from ..yukkuri_components import YukkuriStats, ItemStats
from ..player_components import PlayerState
from ..entity_factory import EntityFactory

class PersistenceSystem(System):
    """
    System responsible for saving and loading the game state.
    """

    def __init__(self):
        pass # self.ecs_world is injected when added to world

    def update(self, world: World, dt: float) -> None:
        # PersistenceSystem doesn't need to do anything every frame
        pass

    def save(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.

        Args:
            filename: The name of the save file. Defaults to "savegame.json".
        """
        if not hasattr(self, 'ecs_world'):
            logger.error("PersistenceSystem not attached to a world.")
            return

        world = self.ecs_world

        # Get player state
        player_entities = world.get_components(PlayerState)
        if not player_entities:
            logger.warning("No PlayerState found. Using default values.")
            player_data = {"money": 0, "time": 0, "save_dir": "saves"}
            save_dir = "saves"
        else:
            # Assuming singleton player
            _, player_state = next(iter(player_entities.items()))
            player_data = {
                "money": player_state.money,
                "time": player_state.time_elapsed,
                "save_dir": player_state.save_dir
            }
            save_dir = player_state.save_dir

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        data: dict[str, Any] = {
            "player": player_data,
            "entities": []
        }

        # Serialize Entities
        # Iterate over all entities with relevant components
        # We can get all entities that have Transform, or YukkuriStats, or ItemStats.

        # A better approach might be to iterate over entities that have Transform
        # and then check for other components.

        transforms = world.get_components(Transform)

        for entity, trans in transforms.items():
            ent_data: Dict[str, Any] = {}
            ent_data["transform"] = {"x": float(trans.x), "y": float(trans.y)}

            # Yukkuri Stats
            y_stats = world.get_component(entity, YukkuriStats)
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
            i_stats = world.get_component(entity, ItemStats)
            if i_stats:
                ent_data["item"] = {
                    "type_id": i_stats.type_id
                }

            # Only save if it's a Yukkuri or Item (ignoring other decorative entities for now if any)
            if "yukkuri" in ent_data or "item" in ent_data:
                 if isinstance(data["entities"], list):
                    data["entities"].append(ent_data)

        path = os.path.join(save_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Game saved to {path}")

    def load(self, filename: str = "savegame.json") -> bool:
        """
        Loads a game state from a JSON file.

        Args:
            filename: The name of the save file. Defaults to "savegame.json".

        Returns:
            bool: True if loading was successful, False otherwise.
        """
        if not hasattr(self, 'ecs_world'):
            logger.error("PersistenceSystem not attached to a world.")
            return False

        world = self.ecs_world

        # Find where to look for the save file.
        # Check existing player state for save dir, or default.
        player_entities = world.get_components(PlayerState)
        if player_entities:
             _, player_state = next(iter(player_entities.items()))
             save_dir = player_state.save_dir
        else:
             save_dir = "saves" # Fallback

        path = os.path.join(save_dir, filename)
        if not os.path.exists(path):
            logger.warning(f"Save file not found at {path}")
            return False

        with open(path, "r") as f:
            data = json.load(f)

        # Load Player State
        player_data = data.get("player", {})
        money = player_data.get("money", 1000)
        time_elapsed = player_data.get("time", 0.0)

        if player_entities:
            _, player_state = next(iter(player_entities.items()))
            player_state.money = money
            player_state.time_elapsed = time_elapsed
        else:
             # If no player entity exists yet, create one.
             # This handles the case where we load into a fresh world.
             player_entity = world.create_entity()
             world.add_component(player_entity, PlayerState(
                 money=money,
                 time_elapsed=time_elapsed,
                 save_dir=save_dir
             ))

        # Clear existing entities (Yukkuris and Items)
        # We iterate over Transform components as a proxy for game entities
        transforms = world.get_components(Transform)
        entities_to_destroy = []
        for entity in transforms:
            # Check if it is NOT the player entity (if player has Transform, which it currently doesn't in my plan, but good to be safe)
            if not world.has_component(entity, PlayerState):
                 entities_to_destroy.append(entity)

        for entity in entities_to_destroy:
             world.destroy_entity(entity)

        # Recreate Entities
        factory = world.services.get(EntityFactory)
        if not factory:
             logger.error("EntityFactory not found in services.")
             return False

        for ent_data in data.get("entities", []):
            trans = ent_data.get("transform")
            x, y = float(trans["x"]), float(trans["y"])

            if "yukkuri" in ent_data:
                y_data = ent_data["yukkuri"]
                eid = factory.create_yukkuri(y_data["type_id"], x, y)
                stats = world.get_component(eid, YukkuriStats)
                if stats:
                    stats.name = y_data["name"]
                    stats.health = float(y_data["health"])
                    stats.hunger = float(y_data["hunger"])
                    stats.happiness = float(y_data["happiness"])
                    stats.badges = int(y_data["badges"])
                    stats.age = float(y_data["age"])

            elif "item" in ent_data:
                i_data = ent_data["item"]
                factory.create_item(i_data["type_id"], x, y)

        logger.info("Game loaded.")
        return True
