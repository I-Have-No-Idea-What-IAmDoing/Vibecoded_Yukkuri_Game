"""
Entity Factory Module.

This module provides a centralized factory for creating various game entities
including Yukkuris, items, and effects. It manages archetype loading and
delegates to specific prefab creation functions.
"""

import tomllib
from pathlib import Path

from loguru import logger

from ..engine.ecs import World
from .prefabs.effects import create_floating_text
from .prefabs.item import create_item, create_poop
from .prefabs.yukkuri import create_yukkuri
from .yukkuri_components import ArchetypeConfig, GoalType


class EntityFactory:
    """
    Factory for creating entities within the game world.
    Delegates specific entity creation logic to prefab functions.

    Attributes:
        world (World): The ECS world instance.
        archetype_cache (dict[str, ArchetypeConfig]): Cache of loaded archetypes.
    """

    def __init__(self, world: World) -> None:
        """
        Initializes the EntityFactory.

        Args:
            world: The ECS world instance.
        """
        self.world = world
        self.archetype_cache: dict[str, ArchetypeConfig] = {}

    def load_archetype(self, archetype_id: str) -> ArchetypeConfig | None:
        """
        Loads an archetype configuration from a TOML file.

        Args:
            archetype_id: The name of the archetype (file name without extension).

        Returns:
            The loaded config, or None if failed.
        """
        if archetype_id in self.archetype_cache:
            return self.archetype_cache[archetype_id]

        path = Path(f"data/archetypes/{archetype_id}.toml")
        if not path.exists():
            logger.warning(f"Archetype file not found: {path}")
            return None

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            config = ArchetypeConfig()
            config.archetype_id = data.get("archetype_id", archetype_id)
            config.stamina_regen = float(data.get("stamina_regen", 10.0))

            # Parse Priorities
            priorities_list = data.get("priorities", {}).get("list", [])
            goal_types = []
            for p_str in priorities_list:
                try:
                    goal_types.append(GoalType[p_str])
                except KeyError:
                    logger.warning(
                        f"Invalid GoalType in archetype {archetype_id}: {p_str}"
                    )
            config.priorities = goal_types

            # Parse Tags
            config.prey_tags = set(data.get("prey_tags", {}).get("tags", []))
            config.predator_tags = set(data.get("predator_tags", {}).get("tags", []))

            # Parse Personality Bias
            config.personality_bias = data.get("personality_bias", {})

            self.archetype_cache[archetype_id] = config
            return config

        except Exception as e:
            logger.error(f"Failed to load archetype {archetype_id}: {e}")
            return None

    def create_yukkuri(
        self,
        type_id: str,
        x: float,
        y: float,
        age: float = 0.0,
        parents: list[int] | None = None,
    ) -> int:
        """
        Creates a Yukkuri entity.

        Args:
            type_id: The type identifier of the Yukkuri (e.g., 'reimu').
            x: The initial x-coordinate.
            y: The initial y-coordinate.
            age: The initial age of the Yukkuri. Defaults to 0.0.
            parents: List of parent entity IDs. Defaults to None.

        Returns:
            The ID of the created entity.
        """
        return create_yukkuri(self.world, type_id, x, y, age, parents)

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an Item entity.

        Args:
            type_id: The type identifier of the item.
            x: The initial x-coordinate.
            y: The initial y-coordinate.

        Returns:
            The ID of the created entity.
        """
        return create_item(self.world, type_id, x, y)

    def create_poop(self, x: float, y: float) -> int:
        """
        Creates a Poop entity.

        Args:
            x: The initial x-coordinate.
            y: The initial y-coordinate.

        Returns:
            The ID of the created entity.
        """
        return create_poop(self.world, x, y)

    def create_floating_text(
        self, x: float, y: float, text: str, color: tuple[int, int, int], size: int = 20
    ) -> int:
        """
        Creates a floating text effect entity.

        Args:
            x: The initial x-coordinate.
            y: The initial y-coordinate.
            text: The text to display.
            color: The RGB color of the text.
            size: The font size. Defaults to 20.

        Returns:
            The ID of the created entity.
        """
        return create_floating_text(self.world, x, y, text, color, size)
