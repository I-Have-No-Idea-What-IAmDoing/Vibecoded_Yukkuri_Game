"""
Module defining core game services.
"""

import os
import json
from typing import Set, TYPE_CHECKING
from loguru import logger

from ..engine.ecs import World
from ..engine.audio import AudioManager
from .components import Transform
from .yukkuri_components import (
    YukkuriStats, ItemStats, AIState, EmotionalState, GossipQueue, Skills
)
from ..engine.serializer import WorldSerializer
from .components_persistence import Persistable, StableIDComponent
from . import components
from . import yukkuri_components
from .skill_constants import SkillId

if TYPE_CHECKING:
    from .yukkuri_components import Personality  # pylint: disable=unused-import
    from .trait_service import TraitService
    from .skill_service import SkillService

BASE_SCAVENGING_RADIUS = 500.0
SCAVENGING_RADIUS_PER_LEVEL = 50.0

class PersistenceService:
    """
    Service responsible for saving and loading game state.

    Attributes:
        world (World): The ECS world instance.
        save_dir (str): The directory to save games in.
        serializer (WorldSerializer): The serializer instance.
    """

    def __init__(self, world: World, save_dir: str = "saves"):
        """
        Initializes the PersistenceService.

        Args:
            world (World): The ECS world instance.
            save_dir (str): The directory path for save files.
        """
        self.world = world
        self.save_dir = save_dir
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except OSError:
                pass  # Might exist or permission error

        # Gather all component types for the serializer
        self.component_types = []
        for module in [components, yukkuri_components]:
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and hasattr(obj, "__dataclass_fields__"):
                    self.component_types.append(obj)
        # Add persistence components
        self.component_types.append(Persistable)
        self.component_types.append(StableIDComponent)

        self.serializer = WorldSerializer(world, self.component_types)

    def save_game(self, filename: str) -> bool:
        """
        Saves the current game state to a JSON file.

        Args:
            filename (str): The name of the save file.

        Returns:
            bool: True if successful, False otherwise.
        """
        filepath = os.path.join(self.save_dir, filename)

        try:
            # 1. Gather Global State
            save_data = {}

            economy = self.world.services.try_get(EconomyService)
            if economy:
                save_data["money"] = economy.get_money()

            time_svc = self.world.services.try_get(TimeService)
            if time_svc:
                save_data["time"] = time_svc.time_elapsed

            # 2. Serialize Entities
            save_data["entities"] = self.serializer.get_persistable_entities_data()

            # 3. Write to File
            with open(filepath, "w") as f:
                json.dump(save_data, f, indent=4)

            logger.info(f"Game saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save game: {e}")
            return False

    def load_game(self, filename: str) -> bool:
        """
        Loads the game state from a JSON file.

        Args:
            filename (str): The name of the save file.

        Returns:
            bool: True if successful, False otherwise.
        """
        filepath = os.path.join(self.save_dir, filename)
        if not os.path.exists(filepath):
            logger.error(f"Save file {filepath} not found.")
            return False

        try:
            with open(filepath, "r") as f:
                save_data = json.load(f)

            # 1. Restore Global State
            if "money" in save_data:
                economy = self.world.services.try_get(EconomyService)
                if economy:
                    economy.set_money(save_data["money"])

            if "time" in save_data:
                time_svc = self.world.services.try_get(TimeService)
                if time_svc:
                    time_svc.time_elapsed = save_data["time"]

            # 2. Restore Entities
            if "entities" in save_data:
                # Clear existing entities? Usually we clear the scene before loading.
                # But here we assume the scene is empty or we are appending.
                # A proper load usually clears the world first.
                # For this service, we just load what's in the file.
                self.serializer.load_from_data(save_data["entities"])

            logger.info(f"Game loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load game: {e}")
            return False

class TimeService:
    """
    Service responsible for tracking game time.

    Attributes:
        _time_elapsed (float): The total elapsed game time in seconds.
    """

    def __init__(self, time_elapsed: float = 0.0) -> None:
        """Initializes the TimeService."""
        self._time_elapsed = time_elapsed

    @property
    def time_elapsed(self) -> float:
        """float: The total elapsed game time in seconds."""
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        self._time_elapsed = value

    def add_time(self, dt: float) -> None:
        """
        Adds time to the total elapsed time.

        Args:
            dt (float): The time delta to add.
        """
        self._time_elapsed += dt

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
            initial_money (int): The starting amount of money.
        """
        self._money = initial_money

    def get_money(self) -> int:
        """Returns the current amount of money."""
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
        self._cleaning_mode = False
        self.hovered_entity_id: int = -1
        self.hovered_entity_pos: tuple[int, int] = (0, 0)

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

    def start_placement(self, type_id: str, cost: int, entity_type: str) -> None:
        """
        Enters placement mode.

        Args:
            type_id (str): The type ID of the entity to place.
            cost (int): The cost of the entity.
            entity_type (str): "yukkuri" or "item".
        """
        self._placing_mode = True
        self._cleaning_mode = False
        self._place_type = type_id
        self._place_cost = cost
        self._place_entity_type = entity_type

    def cancel_placement(self) -> None:
        """Cancels placement mode."""
        self._placing_mode = False
        self._place_type = ""
        self._place_cost = 0
        self._place_entity_type = ""

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

    def find_best_item(self, position: tuple[float, float], stat_criteria: str = "nutrition", exclude_ids: Set[int] | None = None, searcher_id: int = -1) -> int:
        """
        Finds the best item near a position based on criteria.

        Args:
            position (tuple[float, float]): The search origin (x, y).
            stat_criteria (str): The ItemStats attribute to maximize (e.g. "nutrition").
            exclude_ids (Set[int] | None): IDs to ignore.
            searcher_id (int): The ID of the searching entity (optional, for skill checks).

        Returns:
            int: The ID of the best item, or -1 if none found.
        """
        import math

        best_dist = float('inf')
        best_item = -1

        if exclude_ids is None:
            exclude_ids = set()

        # Calculate Search Radius based on Scavenging Skill
        max_radius = float('inf')
        if searcher_id != -1 and self.world.entity_exists(searcher_id):
            skills = self.world.get_component(searcher_id, Skills)
            if skills and SkillId.SCAVENGING in skills.states:
                level = skills.states[SkillId.SCAVENGING].level
                # Base radius 500 + 50 per level
                max_radius = BASE_SCAVENGING_RADIUS + (level * SCAVENGING_RADIUS_PER_LEVEL)
            else:
                # Default radius for unskilled
                max_radius = BASE_SCAVENGING_RADIUS

        items = self.world.get_entities_with(ItemStats, Transform)

        for item in items:
            if item in exclude_ids:
                continue

            istats = self.world.get_component(item, ItemStats)
            itrans = self.world.get_component(item, Transform)

            if istats and itrans and getattr(istats, stat_criteria, 0.0) > 0:
                d = math.hypot(itrans.x - position[0], itrans.y - position[1])

                # Filter by max_radius
                if d > max_radius:
                    continue

                if d < best_dist:
                    best_dist = d
                    best_item = item

        return best_item

    def interact_with_item(self, consumer_id: int, item_id: int, consume: bool = True) -> bool:
        """
        Logic for a Yukkuri interacting with (eating) an item.
        DEPRECATED: Use HungerSystem.
        """
        # Forwarding to system logic or issuing request is possible, but for refactoring
        # we should identify callers and update them.
        # For now, we'll issue an InteractionRequest component so HungerSystem picks it up.
        from .components import InteractionRequest
        if self.world.entity_exists(consumer_id):
            self.world.add_component(consumer_id, InteractionRequest(item_id, consume=consume))
            return True
        return False

    def interact_social(self, initiator_id: int, target_id: int, interaction_type: str) -> bool:
        """
        Logic for social interactions between Yukkuris.
        DEPRECATED: Use SocialSystem via InteractionRequest.
        """
        # Forwarding to system logic via InteractionRequest
        from .components import InteractionRequest
        if self.world.entity_exists(initiator_id) and self.world.entity_exists(target_id):
            self.world.add_component(initiator_id, InteractionRequest(target_id, consume=False, action=interaction_type))
            return True
        return False
