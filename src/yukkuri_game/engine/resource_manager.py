"""
Resource Manager - Asset and Data Loading.

Centralized manager for game resources including images, sounds, and TOML data.
Implements multiple optimization patterns:

Loading Strategies:
- **Lazy Loading**: Game data (types, traits, skills) wrapped in LazyLoader
  to defer file parsing until first access
- **LRU Cache**: Images beyond atlas capacity use OrderedDict LRU eviction
- **Texture Atlas**: Small images packed into single texture for batch rendering

Data Files (TOML):
- YukkuriData: Character type definitions (yukkuris/types.toml)
- ItemData: Item definitions (items/items.toml)
- AIData: Action definitions for utility AI (ai/actions.toml)
- TraitData: Personality trait effects (traits/traits.toml)
- SkillData: Skill definitions (skills/skills.toml)
- InteractionData: Social interaction effects (ai/interactions.toml)

Asset Directories:
- data/: TOML configuration files
- assets/images/: Sprite textures
- assets/sounds/: Audio files
"""

import os
from typing import Any, TypeVar
from collections import OrderedDict

import msgspec
import pygame
from loguru import logger

from .data_models import (
    YukkuriData,
    ItemData,
    AIData,
    GameTuning,
    SkillData,
    TraitData,
    InteractionData,
)
from .atlas import TextureAtlas
from .lazy_loader import LazyLoader

T = TypeVar("T")


class ResourceManager:
    """
    Manages game resources with lazy loading and caching.

    Uses LazyLoader for deferred data file parsing and TextureAtlas
    for efficient sprite rendering. Images fall back to LRU cache
    if atlas capacity is exceeded.
    """

    def __init__(
        self,
        data_dir: str = "data",
        assets_dir: str = "assets",
        image_cache_limit: int = 100,
    ):
        """
        Initializes the ResourceManager.

        Args:
            data_dir (str): The directory path for data files. Defaults to "data".
            assets_dir (str): The directory path for asset files. Defaults to "assets".
            image_cache_limit (int): The maximum number of images to keep in memory. Defaults to 100.
        """
        self.data_dir = data_dir
        self.assets_dir = assets_dir
        # Using OrderedDict for simple LRU if needed, though raw images are usually few
        self.images: OrderedDict[str, pygame.Surface] = OrderedDict()
        self.atlas = TextureAtlas()

        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.configs: dict[str, Any] = {}

        # Cache for loaded data (initialized empty or as LazyLoaders)
        self.yukkuri_types: Any = {}
        self.item_types: Any = {}
        self.ai_actions: Any = {}
        self.tuning: GameTuning | None = None
        self.skills: Any = {}
        self.traits: Any = {}
        self.interactions: Any = {}

        self.image_cache_limit = image_cache_limit

    def load_toml_model(self, filepath: str, model: type[T]) -> T | None:
        """
        Loads a TOML file relative to the data directory and parses it into a msgspec Struct.

        Args:
            filepath (str): The relative path to the TOML file within the data directory.
            model (Type[T]): The msgspec.Struct type to parse into.

        Returns:
            Optional[T]: The parsed data object, or None if loading fails.
        """
        full_path = os.path.join(self.data_dir, filepath)
        try:
            with open(full_path, "rb") as f:  # Binary mode for msgspec.
                data = f.read()

            # noinspection PyTypeChecker
            decoded = msgspec.toml.decode(data, type=model)
            return decoded
        except Exception as e:
            logger.error(f"Failed to load TOML {filepath}: {e}")
            return None

    def save_toml_model(self, filepath: str, data: msgspec.Struct) -> bool:
        """
        Saves a msgspec Struct to a TOML file relative to the data directory.

        Args:
            filepath (str): The relative path to the TOML file within the data directory.
            data (msgspec.Struct): The data to save.

        Returns:
            bool: True if saving succeeded, False otherwise.
        """
        full_path = os.path.join(self.data_dir, filepath)
        try:
            encoded_data = msgspec.toml.encode(data)
            with open(full_path, "wb") as f:
                f.write(encoded_data)
            logger.info(f"Saved TOML: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save TOML {filepath}: {e}")
            return False

    def get_image_path(self, filename: str) -> str:
        """
        Returns the full path to an image file.

        Args:
            filename (str): The filename of the image.

        Returns:
            str: The full path to the image file.
        """
        return os.path.join(self.assets_dir, "images", filename)

    def load_image(self, filename: str) -> pygame.Surface:
        """
        Loads an image relative to the assets/images directory.
        Checks the Atlas first. If valid, adds to Atlas and returns the subsurface.

        Args:
            filename (str): The filename of the image to load.

        Returns:
            pygame.Surface: The loaded image surface or a placeholder.
        """
        # 1. Check Atlas (Already packed?)
        atlas_surf = self.atlas.get_region(filename)
        if atlas_surf:
            return atlas_surf

        if filename in self.images:
            self.images.move_to_end(filename)  # LRU: move to end on access.
            return self.images[filename]

        # 3. Load from Disk
        full_path = self.get_image_path(filename)
        try:
            if not os.path.exists(full_path):
                logger.warning(f"Image not found: {filename}. Creating placeholder.")
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255))  # Magenta placeholder
                self.images[filename] = surf
                return surf

            img = pygame.image.load(full_path).convert_alpha()

            # 4. Try Packing into Atlas
            if self.atlas.add_image(filename, img):
                # Success! Return the subsurface from the atlas
                return self.atlas.get_region(filename)  # type: ignore

            # 5. Fallback to Image Cache if Atlas is full
            self.images[filename] = img
            if len(self.images) > self.image_cache_limit:
                self.images.popitem(last=False)

            return img
        except Exception as e:
            logger.error(f"Failed to load image {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 0))
            return surf

    def load_all_data(self) -> None:
        """
        Sets up LazyLoaders for game data.
        """
        # LazyLoaders defer file parsing until first access.
        # Monolithic TOML files populate the entire cache on first miss.

        self.yukkuri_types = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "yukkuris/types.toml", YukkuriData, "yukkuris", k
            ),
            initializer=lambda: self._load_monolithic(
                "yukkuris/types.toml", YukkuriData, "yukkuris"
            ),
        )

        self.item_types = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "items/items.toml", ItemData, "items", k
            ),
            initializer=lambda: self._load_monolithic(
                "items/items.toml", ItemData, "items"
            ),
        )

        self.ai_actions = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "ai/actions.toml", AIData, "actions", k
            ),
            initializer=lambda: self._load_monolithic(
                "ai/actions.toml", AIData, "actions"
            ),
        )

        self.skills = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "skills/skills.toml", SkillData, "skills", k
            ),
            initializer=lambda: self._load_monolithic(
                "skills/skills.toml", SkillData, "skills"
            ),
        )

        self.traits = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "traits/traits.toml", TraitData, "traits", k
            ),
            initializer=lambda: self._load_monolithic(
                "traits/traits.toml", TraitData, "traits"
            ),
        )

        self.interactions = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "ai/interactions.toml", InteractionData, "interaction", k
            ),
            initializer=lambda: self._load_monolithic(
                "ai/interactions.toml", InteractionData, "interaction"
            ),
        )

        # Tuning is a single object, we can load it immediately as it's small and needed everywhere
        self.tuning = self.load_toml_model("yukkuri_tuning.toml", GameTuning)

        logger.info("Resources configured for Lazy Loading.")

    def _load_monolithic(
        self, file: str, model: type[T], attr: str, requested_key: str | None = None
    ) -> Any:
        """
        Loads a monolithic TOML file and populates the LazyLoader's cache with ALL items found.
        If requested_key is provided, returns the specific item.
        """
        # Determine which LazyLoader to populate based on attr name.
        mapping = getattr(
            self,
            "yukkuri_types"
            if attr == "yukkuris"
            else "item_types"
            if attr == "items"
            else "ai_actions"
            if attr == "actions"
            else "skills"
            if attr == "skills"
            else "traits"
            if attr == "traits"
            else "interactions",
        )

        logger.info(f"Lazy Loading Monolithic File: {file}")
        data = self.load_toml_model(file, model)
        if not data:
            if requested_key:
                raise KeyError(f"Could not load data file {file}")
            return None

        real_dict = getattr(data, attr)

        if isinstance(mapping, LazyLoader):
            for k, v in real_dict.items():
                mapping[k] = v

        if requested_key:
            if requested_key in real_dict:
                return real_dict[requested_key]
            else:
                raise KeyError(f"Key {requested_key} not found in {file}")

        return None

    def clear(self) -> None:
        """
        Clears all loaded resources to free memory.
        """
        self.images.clear()
        # Re-create atlas to clear it
        self.atlas = TextureAtlas()

        self.sounds.clear()
        self.configs.clear()

        # Reset Lazy Loaders
        self.load_all_data()

        self.tuning = None
        logger.info("ResourceManager cleared.")
