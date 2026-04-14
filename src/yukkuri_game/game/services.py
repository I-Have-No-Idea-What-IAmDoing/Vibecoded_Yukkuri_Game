"""
Module defining core game services.
"""

import math
import os
from typing import Any

import msgspec
from loguru import logger

from ..engine.ecs import World
from . import components, components_persistence, yukkuri_components
from .components import Transform
from .skill_constants import SkillId
from .systems.sector_system import SectorMap
from .yukkuri_components import ItemStats, Skills

BASE_SCAVENGING_RADIUS = 500.0
SCAVENGING_RADIUS_PER_LEVEL = 50.0


class TimeService:
    """
    Service responsible for tracking game time.

    Game time runs at a configurable scale relative to physics time.
    Default 60x means 1 physics second = 1 game minute.

    Attributes:
        _time_elapsed (float): The total elapsed game time in seconds.
        _scale (float): Game seconds per physics second.
        _day_start_hour (float): Hour when day begins.
        _night_start_hour (float): Hour when night begins.
        _game_speed (float): User-adjustable multiplier for game time progression.
    """

    GAME_DAY_LENGTH: float = 86400.0  # 24 hours in game seconds

    def __init__(
        self,
        time_elapsed: float = 0.0,
        scale: float = 60.0,
        day_start_hour: float = 6.0,
        night_start_hour: float = 20.0,
    ) -> None:
        """
        Initializes the TimeService.

        Args:
            time_elapsed (float): The initial elapsed game time. Defaults to 0.0.
            scale (float): The game time scale factor. Defaults to 60.0.
            day_start_hour (float): The hour (0-24) when day starts. Defaults to 6.0.
            night_start_hour (float): The hour (0-24) when night starts. Defaults to 20.0.
        """
        self._time_elapsed = time_elapsed
        self._scale = scale
        self._day_start_hour = day_start_hour
        self._night_start_hour = night_start_hour
        self._game_speed = 1.0  # User-controlled speed multiplier (for HUD display)

    @property
    def time_elapsed(self) -> float:
        """float: The total elapsed game time in seconds."""
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        self._time_elapsed = value

    @property
    def scale(self) -> float:
        """float: Current time scale (game seconds per physics second)."""
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = max(0.1, min(value, 1000.0))  # Clamp to reasonable range

    @property
    def game_delta_multiplier(self) -> float:
        """float: Multiplier to convert physics dt to game dt."""
        return self._scale * self._game_speed

    def update(self, physics_dt: float) -> float:
        """
        Update game time based on physics delta.

        Args:
            physics_dt (float): The physics time delta.

        Returns:
            float: The game time delta.
        """
        game_dt = physics_dt * self.game_delta_multiplier
        self._time_elapsed += game_dt
        return game_dt

    @property
    def time_of_day(self) -> float:
        """
        Returns the time of day in hours (0.0 to 24.0).

        Returns:
            float: Time of day in hours.
        """
        return (self._time_elapsed % self.GAME_DAY_LENGTH) / 3600.0

    @property
    def hour_of_day(self) -> float:
        """
        Alias for time_of_day.

        Returns:
            float: Time of day in hours.
        """
        return self.time_of_day

    @property
    def is_night(self) -> bool:
        """
        Returns True if it is currently night time.

        Returns:
            bool: True if it is night.
        """
        t = self.time_of_day
        return t > self._night_start_hour or t < self._day_start_hour

    @property
    def day(self) -> int:
        """
        Returns the current day number (1-indexed).
        Day 1 starts at time_elapsed = 0.

        Returns:
            int: The current day number.
        """
        return int(self._time_elapsed / self.GAME_DAY_LENGTH) + 1

    @property
    def game_speed(self) -> float:
        """float: Current user-controlled game speed multiplier."""
        return self._game_speed

    @game_speed.setter
    def game_speed(self, value: float) -> None:
        self._game_speed = value


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

    @property
    def money(self) -> int:
        """
        Returns the current amount of money.

        Returns:
            int: The current money amount.
        """
        return self._money

    def add_money(self, amount: int) -> None:
        """
        Adds money to the player's funds.

        Args:
            amount (int): The amount to add (must be positive).

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError("Cannot add negative money.")
        self._money += amount

    def remove_money(self, amount: int) -> bool:
        """
        Removes money from the player's funds.

        Args:
            amount (int): The amount to remove (must be positive).

        Returns:
            bool: True if funds were sufficient and removed, False otherwise.

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
        Sets the player's money directly.

        Args:
            amount (int): The new money amount. Clamped to 0 minimum.
        """
        if amount < 0:
            self._money = 0
        else:
            self._money = amount


class InputService:
    """
    Service responsible for managing input state, specifically placement mode and selection.

    Attributes:
        _placing_mode (bool): Whether placement mode is active.
        _place_type (str): The ID of the item/yukkuri being placed.
        _place_cost (int): The cost of the item being placed.
        _place_entity_type (str): The type of entity ("yukkuri" or "item").
        _cleaning_mode (bool): Whether cleaning mode is active.
        hovered_entity_id (int): The ID of the entity under the cursor.
        hovered_entity_pos (tuple[int, int]): Screen position of hovered entity.
        drag_start_pos (tuple[int, int]): Screen position where drag started.
        drag_current_pos (tuple[int, int]): Current screen position during drag.
        is_dragging (bool): Whether a drag operation is in progress.
    """

    def __init__(self) -> None:
        """Initializes the InputService."""
        self._placing_mode = False
        self._place_type: str = ""
        self._place_cost: int = 0
        self._place_entity_type: str = ""  # "yukkuri" or "item"
        self._place_image_name: str = ""
        self._cleaning_mode = False
        self.hovered_entity_id: int = -1
        self.hovered_entity_pos: tuple[int, int] = (0, 0)

        # Current placement position in world coordinates (for preview)
        self.current_placement_pos: tuple[float, float] = (0.0, 0.0)

        # New selection/drag state
        self.drag_start_pos: tuple[int, int] = (0, 0)
        self.drag_current_pos: tuple[int, int] = (0, 0)
        self.is_dragging: bool = False

    @property
    def is_placing(self) -> bool:
        """bool: True if in placement mode."""
        return self._placing_mode

    @property
    def is_cleaning(self) -> bool:
        """bool: True if in cleaning mode."""
        return self._cleaning_mode

    @property
    def place_type(self) -> str:
        """str: ID of the type being placed."""
        return self._place_type

    @property
    def place_cost(self) -> int:
        """int: Cost of the item being placed."""
        return self._place_cost

    @property
    def place_entity_type(self) -> str:
        """str: Type category of the entity being placed."""
        return self._place_entity_type

    @property
    def place_image_name(self) -> str:
        """str: Image name for the preview entity."""
        return self._place_image_name

    def start_placement(
        self, type_id: str, cost: int, entity_type: str, image_name: str = ""
    ) -> None:
        """
        Enters placement mode.

        Args:
            type_id (str): The type ID of the entity to place.
            cost (int): The cost of the entity.
            entity_type (str): "yukkuri" or "item".
            image_name (str): Image name for preview. Defaults to "".
        """
        self._placing_mode = True
        self._cleaning_mode = False
        self._place_type = type_id
        self._place_cost = cost
        self._place_entity_type = entity_type
        self._place_image_name = image_name

    def cancel_placement(self) -> None:
        """Cancels placement mode."""
        self._placing_mode = False
        self._place_type = ""
        self._place_cost = 0
        self._place_entity_type = ""
        self._place_image_name = ""

    def start_cleaning(self) -> None:
        """Enters cleaning mode."""
        self._cleaning_mode = True
        self._placing_mode = False

    def stop_cleaning(self) -> None:
        """Stops cleaning mode."""
        self._cleaning_mode = False


class GameService:
    """
    Service providing game-specific logic and utilities.

    Attributes:
        world (World): The ECS world.
    """

    def __init__(self, world: World):
        """
        Initializes the GameService.

        Args:
            world (World): The ECS World instance.
        """
        self.world = world

    def find_best_item(
        self,
        position: tuple[float, float],
        stat_criteria: str = "nutrition",
        exclude_ids: set[int] | None = None,
        searcher_id: int = -1,
    ) -> int:
        """
        Finds the best item near a position based on criteria.
        Uses SectorMap for efficient spatial query.

        Args:
            position (tuple[float, float]): The search origin (x, y).
            stat_criteria (str): The ItemStats attribute to maximize (e.g. "nutrition"). Defaults to "nutrition".
            exclude_ids (set[int] | None): IDs to ignore. Defaults to None.
            searcher_id (int): The ID of the searching entity (optional, for skill checks). Defaults to -1.

        Returns:
            int: The ID of the best item, or -1 if none found.
        """
        best_dist = float("inf")
        best_item = -1

        if exclude_ids is None:
            exclude_ids = set()

        # Calculate Search Radius based on Scavenging Skill
        max_radius = BASE_SCAVENGING_RADIUS
        if searcher_id != -1 and self.world.entity_exists(searcher_id):
            skills = self.world.get_component(searcher_id, Skills)
            if skills and SkillId.SCAVENGING in skills.states:
                level = skills.states[SkillId.SCAVENGING].level
                max_radius = BASE_SCAVENGING_RADIUS + (
                    level * SCAVENGING_RADIUS_PER_LEVEL
                )

        sector_map = self.world.services.try_get(SectorMap)

        if sector_map:
            nearby_entities = sector_map.get_entities_in_radius(
                position[0], position[1], max_radius
            )

            for item in nearby_entities:
                if item in exclude_ids:
                    continue
                istats = self.world.get_component(item, ItemStats)
                itrans = self.world.get_component(item, Transform)
                if istats and itrans and getattr(istats, stat_criteria, 0.0) > 0:
                    d = math.hypot(itrans.x - position[0], itrans.y - position[1])

                    if d > max_radius:
                        continue

                    if d < best_dist:
                        best_dist = d
                        best_item = item
        else:  # Fallback to linear scan.
            # Optimization: Use get_components_tuple to iterate efficiently
            components = self.world.get_components_tuple(ItemStats, Transform)
            for item, (istats, itrans) in components:
                if item in exclude_ids:
                    continue

                if getattr(istats, stat_criteria, 0.0) > 0:
                    d = math.hypot(itrans.x - position[0], itrans.y - position[1])

                    if d > max_radius:
                        continue

                    if d < best_dist:
                        best_dist = d
                        best_item = item

        return best_item


class PersistenceService:
    """
    Service responsible for saving and loading the game state.

    Attributes:
        world (World): The ECS world instance.
        save_dir (str): Directory where save files are stored.
    """

    def __init__(self, world: World, save_dir: str = "saves"):
        """
        Initializes the PersistenceService.

        Args:
            world (World): The ECS world.
            save_dir (str): Path to the save directory. Defaults to "saves".
        """
        self.world = world
        self.save_dir = save_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def _serialize_object(self, obj: object) -> Any:
        """
        Recursively converts objects to JSON-serializable structures.

        Args:
            obj (object): The object to serialize.

        Returns:
            Any: The serialized object.
        """
        if isinstance(obj, (set, tuple)):
            return list(obj)
        if isinstance(obj, dict):
            return {k: self._serialize_object(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize_object(v) for v in obj]
        return obj

    def save_game(self, filename: str) -> None:
        """
        Saves the current game state to a file.

        Args:
            filename (str): The name of the save file.
        """
        filepath = os.path.join(self.save_dir, filename)

        data = {"money": 0, "time": 0.0, "entities": []}

        # Save Economy
        economy = self.world.services.try_get(EconomyService)
        if economy:
            data["money"] = economy.money

        # Save Time
        time_svc = self.world.services.try_get(TimeService)
        if time_svc:
            data["time"] = time_svc.time_elapsed

        # Gather all component types from modules.
        # This is required by WorldSerializer
        import inspect
        from . import components, components_persistence, yukkuri_components
        from ..engine.serializer import WorldSerializer

        component_types = []
        for module in [components, components_persistence, yukkuri_components]:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and (
                    hasattr(obj, "__dataclass_fields__")
                    or issubclass(obj, msgspec.Struct)
                ):
                    component_types.append(obj)

        serializer = WorldSerializer(self.world, component_types)
        
        # Save Entities
        try:
            data["entities"] = serializer.get_persistable_entities_data()
        except Exception as e:
            logger.error(f"Failed to serialize game state: {e}", exc_info=True)
            raise

        with open(filepath, "wb") as f:
            f.write(msgspec.msgpack.encode(data))

    def load_game(self, filename: str) -> bool:
        """
        Loads the game state from a file.

        Args:
            filename (str): The name of the save file.

        Returns:
            bool: True if successful, False if file not found.
        """
        filepath = os.path.join(self.save_dir, filename)
        if not os.path.exists(filepath):
            return False

        with open(filepath, "rb") as f:
            data = msgspec.msgpack.decode(f.read())

        # Restore Economy
        economy = self.world.services.try_get(EconomyService)
        if economy:
            economy.set_money(data.get("money", 0))

        # Restore Time
        time_svc = self.world.services.try_get(TimeService)
        if time_svc:
            time_svc.time_elapsed = data.get("time", 0.0)

        # Restore Entities
        entities_data = data.get("entities", [])

        # Use WorldSerializer for robust loading and reference remapping
        import inspect

        from ..engine.serializer import WorldSerializer

        # Gather all component types from modules.
        component_types = []
        for module in [components, components_persistence, yukkuri_components]:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and (
                    hasattr(obj, "__dataclass_fields__")
                    or issubclass(obj, msgspec.Struct)
                ):
                    component_types.append(obj)

        serializer = WorldSerializer(self.world, component_types)
        serializer.load_from_data(entities_data)

        return True
