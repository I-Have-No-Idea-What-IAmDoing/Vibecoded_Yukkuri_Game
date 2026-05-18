"""
Module defining core game services.
"""

import collections
import math
from typing import TYPE_CHECKING


from ..engine.ecs import World
from .components import ItemStats, Skills, Transform
from .skill_constants import SkillId
from .systems.spatial_system import SpatialService

if TYPE_CHECKING:
    pass

BASE_SCAVENGING_RADIUS = 500.0
SCAVENGING_RADIUS_PER_LEVEL = 50.0




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


class InputBufferService:
    """
    Service that acts as a FIFO queue of GameCommand objects.

    InputSystem enqueues commands here each frame.
    CommandProcessorSystem drains and executes them at the start of the
    next frame, ensuring all game logic is fully decoupled from raw input.

    Attributes:
        _queue: Internal deque storing pending commands.
    """

    def __init__(self) -> None:
        """Initialises the InputBufferService with an empty command queue."""
        self._queue: collections.deque[object] = collections.deque()

    def add_command(self, command: object) -> None:
        """
        Enqueues a command for deferred execution.

        Args:
            command: Any object satisfying the GameCommand protocol.
        """
        self._queue.append(command)

    def pop_all(self) -> list[object]:
        """
        Drains the queue and returns all pending commands.

        Clears the internal queue in one atomic swap so that commands
        added during execution are deferred to the *next* frame.

        Returns:
            list[object]: All commands that were pending at call time.
        """
        pending = list(self._queue)
        self._queue.clear()
        return pending


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
        Uses SpatialService for efficient spatial query.

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
            skills = self.world.try_get_component(searcher_id, Skills)
            if skills and SkillId.SCAVENGING in skills.states:
                level = skills.states[SkillId.SCAVENGING].level
                max_radius = BASE_SCAVENGING_RADIUS + (
                    level * SCAVENGING_RADIUS_PER_LEVEL
                )

        spatial_service = self.world.services.try_get(SpatialService)

        if spatial_service:
            nearby_entities = spatial_service.get_entities_in_radius(
                position[0], position[1], max_radius
            )

            for item in nearby_entities:
                if item in exclude_ids:
                    continue
                istats = self.world.try_get_component(item, ItemStats)
                if not istats:
                    continue
                itrans = self.world.try_get_component(item, Transform)
                if not itrans:
                    continue
                if getattr(istats, stat_criteria, 0.0) > 0:
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


