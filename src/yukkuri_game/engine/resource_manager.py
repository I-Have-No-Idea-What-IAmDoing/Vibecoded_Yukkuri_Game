"""
Resource Manager Module.

This module provides the `ResourceManager` class, which handles the loading, caching,
and lifecycle management of game assets (images, sounds) and data files (TOML primitives).
It implements lazy loading for data files to optimize startup time and memory usage.
"""

import os
from collections import OrderedDict
from typing import Any, TypeVar

import msgspec
import pygame
from loguru import logger

from .atlas import TextureAtlas
from .data_models import (
    AIData,
    GameTuning,
    InteractionData,
    ItemData,
    SkillData,
    TraitData,
    YukkuriData,
)
from .exceptions import ResourceLoadError
from .lazy_loader import LazyLoader

T = TypeVar("T")

YUKKURI_TYPES_FILE = "yukkuris/types.toml"
ITEMS_FILE = "items/items.toml"
AI_ACTIONS_FILE = "ai/actions.toml"
SKILLS_FILE = "skills/skills.toml"
TRAITS_FILE = "traits/traits.toml"
INTERACTIONS_FILE = "ai/interactions.toml"

# Maps monolithic TOML attribute names to the corresponding LazyLoader field on the ResourceManager.
ATTR_TO_LOADER = {
    "yukkuris": "yukkuri_types",
    "items": "item_types",
    "actions": "ai_actions",
    "skills": "skills",
    "traits": "traits",
    "interaction": "interactions",
}


class ResourceManager:
    """
    Manages loading and caching of game resources.

    This class serves as the central access point for all game assets. It employs
    several optimization strategies:
    1.  **Lazy Loading**: Data files are parsed only when accessed.
    2.  **Texture Atlas**: Small images are packed into a single large texture to minimize state changes during rendering.
    3.  **LRU Caching**: Individual images are cached with an LRU eviction policy if the atlas is full or unavailable.

    Attributes:
        data_dir (str): Relative path to the directory containing data files.
        assets_dir (str): Relative path to the directory containing assets.
        image_cache_limit (int): Maximum number of individual images to hold in the LRU cache.
        images (OrderedDict[str, pygame.Surface]): LRU cache of loaded image surfaces.
        atlas (TextureAtlas): Dynamic texture atlas for efficient sprite management.
        sounds (dict[str, pygame.mixer.Sound]): Cache of loaded sound effects.
        configs (dict[str, Any]): General configuration storage.
        yukkuri_types (LazyLoader): Lazy-loaded registry of Yukkuri definitions.
        item_types (LazyLoader): Lazy-loaded registry of item definitions.
        ai_actions (LazyLoader): Lazy-loaded registry of AI actions.
        tuning (GameTuning | None): Global game tuning parameters (loaded eagerly).
        skills (LazyLoader): Lazy-loaded registry of skills.
        traits (LazyLoader): Lazy-loaded registry of traits.
        interactions (LazyLoader): Lazy-loaded registry of interaction definitions.
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
            data_dir (str): Directory containing TOML data files. Defaults to "data".
            assets_dir (str): Directory containing image and sound assets. Defaults to "assets".
            image_cache_limit (int): Maximum items for the image LRU cache. Defaults to 100.
        """
        self.data_dir = data_dir
        self.assets_dir = assets_dir
        self.images: OrderedDict[str, pygame.Surface] = OrderedDict()
        self.atlas = TextureAtlas()

        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.configs: dict[str, Any] = {}

        # Optimized data structures using LazyLoader to defer parsing cost.
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
        Loads and parses a TOML file into a structured model.

        Args:
            filepath (str): Path to the TOML file, relative to `self.data_dir`.
            model (type[T]): The `msgspec.Struct` type definition to parse the data into.

        Returns:
            T | None: The parsed data object of type `T`, or None if the operation fails.
        """
        full_path = os.path.join(self.data_dir, filepath)
        try:
            with open(full_path, "rb") as f:
                data = f.read()

            # msgspec is highly optimized for performance.
            # noinspection PyTypeChecker
            decoded = msgspec.toml.decode(data, type=model)
            return decoded
        except Exception as e:
            logger.error(f"Failed to load TOML {filepath}: {e}")
            return None

    def save_toml_model(self, filepath: str, data: msgspec.Struct) -> bool:
        """
        Serializes and saves a structured model to a TOML file.

        Args:
            filepath (str): Destination path, relative to `self.data_dir`.
            data (msgspec.Struct): The `msgspec.Struct` object to serialize.

        Returns:
            bool: True if the file was successfully written, False otherwise.
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
        Resolves the absolute path for an image file.

        Args:
            filename (str): Name of the image file (e.g., "sprite.png").

        Returns:
            str: The absolute file path to the image.
        """
        return os.path.join(self.assets_dir, "images", filename)

    def load_image(self, filename: str) -> pygame.Surface:
        """
        Retrieves an image, utilizing the texture atlas and cache.

        Strategies in order:
        1. Check if the image is already in the TextureAtlas.
        2. Check the LRU image cache.
        3. Load from disk.
        4. Attempt to pack into the TextureAtlas.
        5. Store in LRU cache if packing fails.

        Args:
            filename (str): The filename of the image to load.

        Returns:
            pygame.Surface: The requested pygame.Surface. Returns a magenta placeholder if loading fails.
        """
        # Strategy 1: Atlas Lookup
        atlas_surf = self.atlas.get_region(filename)
        if atlas_surf:
            return atlas_surf

        # Strategy 2: LRU Cache Lookup
        if filename in self.images:
            self.images.move_to_end(filename)
            return self.images[filename]

        # Strategy 3: Disk Load
        full_path = self.get_image_path(filename)
        try:
            if not os.path.exists(full_path):
                logger.warning(f"Image not found: {filename}. Creating placeholder.")
                # Return visible error texture (magenta)
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255))
                self.images[filename] = surf
                return surf

            img = pygame.image.load(full_path).convert_alpha()

            # Strategy 4: Atlas Packing
            # Attempt to add to dynamic atlas for batching benefits
            if self.atlas.add_image(filename, img):
                return self.atlas.get_region(filename)  # type: ignore

            # Strategy 5: Cache Fallback
            # If atlas is full or image type is unsuitable, use standard LRU cache
            self.images[filename] = img
            if len(self.images) > self.image_cache_limit:
                self.images.popitem(last=False)

            return img
        except Exception as e:
            logger.error(f"Failed to load image {filename}: {e}")
            # Return critical error texture (red)
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 0))
            return surf

    def load_all_data(self) -> None:
        """
        Initializes the data registries using LazyLoaders.

        This setup ensures that monolithic TOML files are not parsed until a specific
        resource from them is requested, significantly improving initial startup time.
        """
        self.yukkuri_types = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                YUKKURI_TYPES_FILE, YukkuriData, "yukkuris", k
            ),
            initializer=lambda: self._load_monolithic(
                YUKKURI_TYPES_FILE, YukkuriData, "yukkuris"
            ),
        )

        self.item_types = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                ITEMS_FILE, ItemData, "items", k
            ),
            initializer=lambda: self._load_monolithic(ITEMS_FILE, ItemData, "items"),
        )

        self.ai_actions = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                AI_ACTIONS_FILE, AIData, "actions", k
            ),
            initializer=lambda: self._load_monolithic(
                AI_ACTIONS_FILE, AIData, "actions"
            ),
        )

        self.skills = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                SKILLS_FILE, SkillData, "skills", k
            ),
            initializer=lambda: self._load_monolithic(SKILLS_FILE, SkillData, "skills"),
        )

        self.traits = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                TRAITS_FILE, TraitData, "traits", k
            ),
            initializer=lambda: self._load_monolithic(TRAITS_FILE, TraitData, "traits"),
        )

        self.interactions = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                INTERACTIONS_FILE, InteractionData, "interaction", k
            ),
            initializer=lambda: self._load_monolithic(
                INTERACTIONS_FILE, InteractionData, "interaction"
            ),
        )

        # Tuning data is small and accessed frequently, so we load it eagerly.
        self.tuning = self.load_toml_model("yukkuri_tuning.toml", GameTuning)

        logger.info("Resources configured for Lazy Loading.")

    def _load_monolithic(
        self, file: str, model: type[T], attr: str, requested_key: str | None = None
    ) -> Any:
        """
        Helper to handle monolithic file loading for LazyLoaders.

        Parses the entire file and populates the cache. If a specific key was requested,
        it returns that specific item after populating the cache.

        Args:
            file (str): TOML filename.
            model (type[T]): Data model class.
            attr (str): Attribute name in the data model that contains the dictionary of items.
            requested_key (str | None): Specific key to return immediately (optional).

        Returns:
            Any: The requested item if `requested_key` is provided, otherwise None.

        Raises:
            ResourceLoadError: If the file cannot be loaded or the requested key is missing.
        """
        # Determine which LazyLoader to populate based on attr name.
        loader_name = ATTR_TO_LOADER.get(attr, attr)
        mapping = getattr(self, loader_name)

        logger.info(f"Lazy Loading Monolithic File: {file}")
        data = self.load_toml_model(file, model)
        if not data:
            logger.error(f"Failed to load critical data file: {file}")
            raise ResourceLoadError(f"Failed to load critical data file: {file}")

        real_dict = getattr(data, attr)

        # Populate the LazyLoader's internal cache with all items found in the file.
        if isinstance(mapping, LazyLoader):
            for k, v in real_dict.items():
                mapping[k] = v

        if requested_key:
            if requested_key in real_dict:
                return real_dict[requested_key]
            else:
                logger.error(
                    f"Key '{requested_key}' not found in {file} (Attribute: {attr})"
                )
                raise ResourceLoadError(
                    f"Key '{requested_key}' not found in {file} (Attribute: {attr})"
                )

        return None

    def clear(self) -> None:
        """
        Resets the resource manager state.

        Clears all caches (images, sounds, configs) and resets LazyLoaders.
        Used to free memory or reset game state.
        """
        self.images.clear()
        # Create a fresh atlas
        self.atlas = TextureAtlas()

        self.sounds.clear()
        self.configs.clear()

        # Reset Lazy Loaders
        self.load_all_data()

        self.tuning = None
        logger.info("ResourceManager cleared.")
