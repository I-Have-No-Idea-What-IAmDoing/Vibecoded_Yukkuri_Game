"""
Module defining service protocols for Inversion of Control in the ECS engine.
"""

from collections.abc import Callable
from typing import Any
from typing import Protocol
from typing import runtime_checkable

import pymunk


@runtime_checkable
class IPhysicsService(Protocol):
    """
    Protocol defining the interface for the Physics Service.
    """

    @property
    def space(self) -> pymunk.Space:
        """
        Gets the underlying Pymunk space.

        Returns:
            pymunk.Space: The active physics space.
        """
        ...

    def clear(self) -> None:
        """
        Clears all bodies, shapes, and constraints from the physics space.
        """
        ...


@runtime_checkable
class IAudioProvider(Protocol):
    """
    Protocol defining the interface for the Audio Service provider.
    """

    enabled: bool

    def load_from_config(self, config_path: str = "data/sounds.toml") -> None:
        """
        Loads sounds from a configuration file.

        Args:
            config_path: Path to the sounds configuration file.
        """
        ...

    def preload_sound(self, name: str, filepath: str) -> None:
        """
        Loads a sound and safeguards it from LRU eviction.

        Args:
            name: The sound identifier name.
            filepath: Path to the sound file.
        """
        ...

    def load_sound(self, name: str, filepath: str) -> None:
        """
        Loads a sound into the sound cache.

        Args:
            name: The sound identifier name.
            filepath: Path to the sound file.
        """
        ...

    def play_sound(self, name: str) -> None:
        """
        Plays a sound by name.

        Args:
            name: The sound identifier name.
        """
        ...

    def play_music(
        self, filepath: str, loops: int = -1, fade_ms: int = 1000
    ) -> None:
        """
        Plays background music from a file.

        Args:
            filepath: Path to the music file.
            loops: Number of loops, -1 for infinite.
            fade_ms: Fade-in duration in milliseconds.
        """
        ...

    def set_master_volume(self, volume: float) -> None:
        """
        Sets the global master volume.

        Args:
            volume: Master volume level between 0.0 and 1.0.
        """
        ...

    def set_bgm_volume(self, volume: float) -> None:
        """
        Sets the background music volume.

        Args:
            volume: BGM volume level between 0.0 and 1.0.
        """
        ...

    def set_sfx_volume(self, volume: float) -> None:
        """
        Sets the sound effects volume.

        Args:
            volume: SFX volume level between 0.0 and 1.0.
        """
        ...

    def clear(self) -> None:
        """
        Stops playback and clears the sound cache of non-preloaded sounds.
        """
        ...


@runtime_checkable
class ISpatialService(Protocol):
    """
    Protocol defining the interface for the Spatial Proximity Service.
    """

    entity_sectors: dict[int, tuple[int, int]]
    body_to_entity: dict[pymunk.Body, int]

    def clear(self) -> None:
        """
        Clears all stored entities from the index.
        """
        ...


    def update_entity(self, entity_id: int, x: float, y: float) -> None:
        """
        Updates the spatial partitioning index for an entity's new position.

        Args:
            entity_id: The ID of the entity.
            x: The new X coordinate.
            y: The new Y coordinate.
        """
        ...

    def remove_entity(self, entity_id: int) -> None:
        """
        Removes an entity from the spatial index.

        Args:
            entity_id: The ID of the entity to remove.
        """
        ...

    def get_entities_in_sector(self, col: int, row: int) -> set[int]:
        """
        Retrieves all entity IDs present in a specific grid sector.

        Args:
            col: The sector column coordinate.
            row: The sector row coordinate.

        Returns:
            set[int]: Set of entity IDs in the sector.
        """
        ...

    def get_entities_in_range(
        self, x: float, y: float, range_type: str = "visual"
    ) -> list[int]:
        """
        Retrieves entities within a range category from a position.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            range_type: The range classification (e.g. 'visual').

        Returns:
            list[int]: List of entity IDs in range.
        """
        ...

    def get_entities_in_radius(
        self, x: float, y: float, radius: float
    ) -> list[int]:
        """
        Retrieves entity IDs within a certain bounding radius.

        Args:
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Bounding query radius.

        Returns:
            list[int]: List of entity IDs within the radius.
        """
        ...

    def get_entities_in_rect(
        self, x: float, y: float, width: float, height: float
    ) -> list[int]:
        """
        Retrieves entity IDs within a rectangular bounding box.

        Args:
            x: Bottom-left/Top-left X coordinate.
            y: Bottom-left/Top-left Y coordinate.
            width: Width of the rect.
            height: Height of the rect.

        Returns:
            list[int]: List of entity IDs within the box.
        """
        ...

    def get_nearest_entity(
        self,
        world: Any,
        x: float,
        y: float,
        component_filter: type | None = None,
        max_radius: float = 1000.0,
        exclude_ids: set[int] | None = None,
        predicate: Callable[[int], bool] | None = None,
    ) -> int:
        """
        Finds the closest entity matching filters.

        Args:
            world: The ECS World context.
            x: Reference X coordinate.
            y: Reference Y coordinate.
            component_filter: Required component type.
            max_radius: Maximum search radius.
            exclude_ids: Entity IDs to exclude.
            predicate: Custom filter Callable.

        Returns:
            int: Closest entity ID or -1 if none found.
        """
        ...

    def raycast(
        self,
        world: Any,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        shape_filter: pymunk.ShapeFilter | None = None,
        exclude_id: int = -1,
    ) -> tuple[int, float, float] | None:
        """
        Performs a raycast segment query in the physics space.

        Args:
            world: The ECS World context.
            start_x: Segment start X coordinate.
            start_y: Segment start Y coordinate.
            end_x: Segment end X coordinate.
            end_y: Segment end Y coordinate.
            shape_filter: Segment filter properties.
            exclude_id: Entity ID to ignore.

        Returns:
            tuple[int, float, float] or None: Hit entity ID and coordinates.
        """
        ...
