import os
import json
from typing import Dict, Any, List, TYPE_CHECKING
from loguru import logger
from ..engine.ecs import World
from .components import Transform
from .yukkuri_components import YukkuriStats, ItemStats
from ..engine.service_locator import ServiceLocator

if TYPE_CHECKING:
    from .entity_factory import EntityFactory

class TimeService:
    """
    Service responsible for tracking game time.
    """
    def __init__(self):
        self._time_elapsed = 0.0

    @property
    def time_elapsed(self) -> float:
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        self._time_elapsed = value

    def add_time(self, dt: float) -> None:
        self._time_elapsed += dt


class PersistenceService:
    """
    Service responsible for saving and loading game state.
    """
    def __init__(self, world: World, save_dir: str = "saves"):
        self.world = world
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.
        """
        economy_service = self.world.services.try_get(EconomyService)
        money = economy_service.get_money() if economy_service else 0

        time_service = self.world.services.try_get(TimeService)
        time_elapsed = time_service.time_elapsed if time_service else 0.0

        data: Dict[str, Any] = {
            "money": money,
            "time": time_elapsed,
            "entities": []
        }

        # Use public API to get all entities.
        try:
            all_entities = self.world.get_all_entities()
        except AttributeError:
             # Fallback if ECS doesn't have get_all_entities
             # Use transform as proxy, but this is not ideal
             logger.warning("World.get_all_entities not available. Falling back to Transform-based iteration.")
             all_entities = self.world.get_entities_with(Transform)

        for entity in all_entities:
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

            if "yukkuri" in ent_data or "item" in ent_data:
                 data["entities"].append(ent_data)

        path = os.path.join(self.save_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Game saved to {path}")

    def load_game(self, filename: str = "savegame.json") -> bool:
        """
        Loads a game state from a JSON file.
        """
        path = os.path.join(self.save_dir, filename)
        if not os.path.exists(path):
            logger.warning("Save file not found.")
            return False

        with open(path, "r") as f:
            data = json.load(f)

        economy_service = self.world.services.try_get(EconomyService)
        if economy_service:
            # We need a way to set money. I'll add set_money to EconomyService.
            if hasattr(economy_service, 'set_money'):
                economy_service.set_money(data.get("money", 1000))
            else:
                # If no set_money, maybe add/remove to match?
                current = economy_service.get_money()
                target = data.get("money", 1000)
                if target > current:
                    economy_service.add_money(target - current)
                elif target < current:
                    economy_service.remove_money(current - target)

        time_service = self.world.services.try_get(TimeService)
        if time_service:
             time_service.time_elapsed = data.get("time", 0.0)

        # Clear existing entities
        try:
            all_entities = self.world.get_all_entities()
            for entity in all_entities:
                self.world.destroy_entity(entity)
        except AttributeError:
             pass

        from .entity_factory import EntityFactory
        factory = self.world.services.get(EntityFactory)

        for ent_data in data.get("entities", []):
            trans = ent_data.get("transform")
            if trans:
                x, y = float(trans["x"]), float(trans["y"])
            else:
                x, y = 0.0, 0.0

            if "yukkuri" in ent_data:
                y_data = ent_data["yukkuri"]
                eid = factory.create_yukkuri(y_data["type_id"], x, y)
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
                factory.create_item(i_data["type_id"], x, y)

        logger.info("Game loaded.")
        return True

class EconomyService:
    """
    Service responsible for managing the player's economy.
    """
    def __init__(self, initial_money: int = 1000):
        self._money = initial_money

    def get_money(self) -> int:
        return self._money

    def add_money(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot add negative money.")
        self._money += amount

    def remove_money(self, amount: int) -> bool:
        """
        Removes money. Returns True if successful, False if insufficient funds.
        """
        if amount < 0:
             raise ValueError("Cannot remove negative money.")
        if self._money >= amount:
            self._money -= amount
            return True
        return False

    def set_money(self, amount: int) -> None:
        if amount < 0:
             self._money = 0
        else:
             self._money = amount


class InputService:
    """
    Service responsible for managing input state, specifically placement mode.
    """
    def __init__(self):
        self._placing_mode = False
        self._place_type: str = ""
        self._place_cost: int = 0
        self._place_entity_type: str = "" # "yukkuri" or "item"

    @property
    def is_placing(self) -> bool:
        return self._placing_mode

    @property
    def place_type(self) -> str:
        return self._place_type

    @property
    def place_cost(self) -> int:
        return self._place_cost

    @property
    def place_entity_type(self) -> str:
        return self._place_entity_type

    def start_placement(self, type_id: str, cost: int, entity_type: str) -> None:
        self._placing_mode = True
        self._place_type = type_id
        self._place_cost = cost
        self._place_entity_type = entity_type

    def cancel_placement(self) -> None:
        self._placing_mode = False
        self._place_type = ""
        self._place_cost = 0
        self._place_entity_type = ""
