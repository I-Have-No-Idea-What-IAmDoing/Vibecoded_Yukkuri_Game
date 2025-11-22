import os
import json
from typing import Dict, Any, List, TYPE_CHECKING
from loguru import logger
from ..engine.ecs import World
from ..engine.audio import AudioManager
from .components import Transform
from .yukkuri_components import YukkuriStats, ItemStats, AIState
from ..engine.service_locator import ServiceLocator

if TYPE_CHECKING:
    from .entity_factory import EntityFactory

class TimeService:
    """
    Service responsible for tracking game time.

    Attributes:
        _time_elapsed (float): The total elapsed game time in seconds.
    """
    def __init__(self) -> None:
        """Initializes the TimeService."""
        self._time_elapsed = 0.0

    @property
    def time_elapsed(self) -> float:
        """
        Gets the total elapsed game time.

        Returns:
            float: The time elapsed in seconds.
        """
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        """
        Sets the total elapsed game time.

        Args:
            value (float): The new time elapsed in seconds.
        """
        self._time_elapsed = value

    def add_time(self, dt: float) -> None:
        """
        Advances the game time.

        Args:
            dt (float): The amount of time to add in seconds.
        """
        self._time_elapsed += dt


class PersistenceService:
    """
    Service responsible for saving and loading game state.

    Attributes:
        world (World): The ECS World instance.
        save_dir (str): The directory where save files are stored.
    """
    def __init__(self, world: World, save_dir: str = "saves"):
        """
        Initializes the PersistenceService.

        Args:
            world (World): The ECS World instance.
            save_dir (str): The directory to store save files. Defaults to "saves".
        """
        self.world = world
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def save_game(self, filename: str = "savegame.json") -> None:
        """
        Saves the current game state to a JSON file.

        Args:
            filename (str): The name of the save file. Defaults to "savegame.json".
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

        # First pass: Create ID mapping for all entities to be saved.
        # We iterate through all entities, but we only assign SaveIDs to those that will be saved.
        # However, since we don't know which ones are saved until we check components,
        # we'll do the filtering logic twice or store the list.

        entities_to_save = []
        id_map: Dict[int, int] = {}

        for entity in all_entities:
            # Check if it's a saveable entity (has YukkuriStats or ItemStats)
            if self.world.has_component(entity, YukkuriStats) or self.world.has_component(entity, ItemStats):
                save_id = len(entities_to_save)
                id_map[entity] = save_id
                entities_to_save.append(entity)

        for entity in entities_to_save:
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

            # AI State
            ai = self.world.get_component(entity, AIState)
            if ai:
                mapped_target_id = id_map.get(ai.current_target_id, -1)
                ent_data["ai_state"] = {
                    "current_action": ai.current_action,
                    "current_target_id": mapped_target_id,
                    "action_progress": float(ai.action_progress),
                    "state_data": ai.state_data,
                    # Helper to convert path tuples to list if needed (json handles list of lists)
                    "path": [list(p) for p in ai.path] if ai.path else None
                }

            data["entities"].append(ent_data)

        path = os.path.join(self.save_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Game saved to {path}")

    def load_game(self, filename: str = "savegame.json") -> bool:
        """
        Loads a game state from a JSON file.

        Args:
            filename (str): The name of the save file. Defaults to "savegame.json".

        Returns:
            bool: True if loading was successful, False otherwise.
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

        # Map SaveID (index in data list) -> NewEntityID
        loaded_entities: List[int] = []

        entities_data = data.get("entities", [])

        # First pass: Create entities
        for ent_data in entities_data:
            trans = ent_data.get("transform")
            if trans:
                x, y = float(trans["x"]), float(trans["y"])
            else:
                x, y = 0.0, 0.0

            eid = -1
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
                eid = factory.create_item(i_data["type_id"], x, y)

            # We append eid even if it's -1 (failed creation) to keep index sync
            loaded_entities.append(eid)

        # Second pass: Restore AI State
        for index, ent_data in enumerate(entities_data):
            eid = loaded_entities[index]
            if eid == -1:
                continue

            if "ai_state" in ent_data:
                ai_data = ent_data["ai_state"]

                # Ensure entity has AIState component
                if not self.world.has_component(eid, AIState):
                    self.world.add_component(eid, AIState())

                ai = self.world.get_component(eid, AIState)
                if ai:
                    ai.current_action = ai_data.get("current_action", "Idle")
                    ai.action_progress = float(ai_data.get("action_progress", 0.0))
                    ai.state_data = ai_data.get("state_data")
                    ai.path = ai_data.get("path")

                    # Resolve target ID
                    saved_target_id = ai_data.get("current_target_id", -1)
                    if saved_target_id != -1 and 0 <= saved_target_id < len(loaded_entities):
                        ai.current_target_id = loaded_entities[saved_target_id]
                    else:
                        ai.current_target_id = -1

        logger.info("Game loaded.")
        return True

class EconomyService:
    """
    Service responsible for managing the player's economy.

    Attributes:
        _money (int): The current amount of money.
    """
    def __init__(self, initial_money: int = 1000):
        """
        Initializes the EconomyService.

        Args:
            initial_money (int): The starting amount of money. Defaults to 1000.
        """
        self._money = initial_money

    def get_money(self) -> int:
        """
        Gets the current amount of money.

        Returns:
            int: The current money.
        """
        return self._money

    def add_money(self, amount: int) -> None:
        """
        Adds money to the player's balance.

        Args:
            amount (int): The amount to add. Must be non-negative.

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError("Cannot add negative money.")
        self._money += amount

    def remove_money(self, amount: int) -> bool:
        """
        Removes money from the player's balance.

        Args:
            amount (int): The amount to remove. Must be non-negative.

        Returns:
            bool: True if successful, False if insufficient funds.

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
             raise ValueError("Cannot remove negative money.")
        if self._money >= amount:
            self._money -= amount
            return True
        return False

    def set_money(self, amount: int) -> None:
        """
        Sets the player's balance to a specific amount.

        Args:
            amount (int): The new balance. If negative, sets to 0.
        """
        if amount < 0:
             self._money = 0
        else:
             self._money = amount


class InputService:
    """
    Service responsible for managing input state, specifically placement mode and selection.
    """
    def __init__(self):
        """Initializes the InputService."""
        self._placing_mode = False
        self._place_type: str = ""
        self._place_cost: int = 0
        self._place_entity_type: str = "" # "yukkuri" or "item"
        self._cleaning_mode = False
        self.hovered_entity_id: int = -1
        self.hovered_entity_pos: tuple[int, int] = (0, 0)

        # New selection/drag state
        self.drag_start_pos: tuple[int, int] = (0, 0)
        self.drag_current_pos: tuple[int, int] = (0, 0)
        self.is_dragging: bool = False

    @property
    def is_placing(self) -> bool:
        """
        Checks if the game is currently in placement mode.

        Returns:
            bool: True if in placement mode, False otherwise.
        """
        return self._placing_mode

    @property
    def is_cleaning(self) -> bool:
        """
        Checks if the game is currently in cleaning mode.

        Returns:
            bool: True if in cleaning mode, False otherwise.
        """
        return self._cleaning_mode

    @property
    def place_type(self) -> str:
        """
        Gets the type identifier of the entity being placed.

        Returns:
            str: The type identifier.
        """
        return self._place_type

    @property
    def place_cost(self) -> int:
        """
        Gets the cost of the entity being placed.

        Returns:
            int: The cost in money.
        """
        return self._place_cost

    @property
    def place_entity_type(self) -> str:
        """
        Gets the general category of the entity being placed.

        Returns:
            str: The entity type (e.g., "yukkuri", "item").
        """
        return self._place_entity_type

    def start_placement(self, type_id: str, cost: int, entity_type: str) -> None:
        """
        Starts the placement mode for a specific entity.

        Args:
            type_id (str): The specific type identifier.
            cost (int): The cost of placing the entity.
            entity_type (str): The category of entity.
        """
        self._placing_mode = True
        self._cleaning_mode = False
        self._place_type = type_id
        self._place_cost = cost
        self._place_entity_type = entity_type

    def cancel_placement(self) -> None:
        """
        Cancels the current placement mode.
        """
        self._placing_mode = False
        self._place_type = ""
        self._place_cost = 0
        self._place_entity_type = ""

    def start_cleaning(self) -> None:
        """
        Starts the cleaning tool mode.
        """
        self._cleaning_mode = True
        self._placing_mode = False

    def stop_cleaning(self) -> None:
        """
        Stops the cleaning tool mode.
        """
        self._cleaning_mode = False


class GameService:
    """
    Service providing game-specific logic and utilities.
    """
    def __init__(self, world: World):
        """
        Initializes the GameService.

        Args:
            world (World): The ECS World instance.
        """
        self.world = world

    def find_best_item(self, position: tuple[float, float], stat_criteria: str = "nutrition") -> int:
        """
        Finds the best item (closest and relevant) for the entity at the given position.

        Args:
            position (tuple[float, float]): The (x, y) position of the searching entity.
            stat_criteria (str): The item stat to look for (e.g., "nutrition", "fun", "comfort").

        Returns:
            int: The entity ID of the best item, or -1 if none found.
        """
        import math
        best_dist = float('inf')
        best_item = -1

        # Assuming ItemStats and Transform are imported or available via world queries
        # We need to import them inside methods or ensure they are available
        from .components import Transform
        from .yukkuri_components import ItemStats

        items = self.world.get_entities_with(ItemStats, Transform)

        for item in items:
            istats = self.world.get_component(item, ItemStats)
            itrans = self.world.get_component(item, Transform)

            # Check if the item has the desired stat and it is greater than 0
            if istats and itrans and getattr(istats, stat_criteria, 0.0) > 0:
                d = math.hypot(itrans.x - position[0], itrans.y - position[1])
                if d < best_dist:
                    best_dist = d
                    best_item = item

        return best_item

