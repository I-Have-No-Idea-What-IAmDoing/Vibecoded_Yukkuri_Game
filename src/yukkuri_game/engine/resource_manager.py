"""
Module for managing game resources like images, sounds, and data files.
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

T = TypeVar("T")


from .atlas import TextureAtlas
from .lazy_loader import LazyLoader


class ResourceManager:
    """
    Manages game resources such as images, sounds, and configuration files.

    Attributes:
        data_dir (str): The directory containing data files (TOML).
        assets_dir (str): The directory containing asset files (images, sounds).
        images (Dict[str, pygame.Surface]): A cache of loaded images.
        atlas (TextureAtlas): The runtime texture atlas.
        sounds (Dict[str, pygame.mixer.Sound]): A cache of loaded sounds.
        configs (Dict[str, Any]): A cache of loaded configurations.
        yukkuri_types (MutableMapping[str, YukkuriType]): Loaded Yukkuri type definitions.
        item_types (MutableMapping[str, ItemType]): Loaded Item type definitions.
        ai_actions (MutableMapping[str, AIAction]): Loaded AI action definitions.
        tuning (Optional[GameTuning]): Loaded game tuning parameters.
        skills (MutableMapping[str, SkillDefinition]): Loaded skill definitions.
        traits (MutableMapping[str, TraitDefinition]): Loaded trait definitions.
        interactions (MutableMapping[str, InteractionDefinition]): Loaded interaction definitions.
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

        # Max number of images to keep in memory (usually base images are few, but good to have a limit)
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
            # We open in binary mode because msgspec handles decoding.
            # If explicit text reading is needed, use encoding="utf-8".
            with open(full_path, "rb") as f:
                data = f.read()

            # noinspection PyTypeChecker
            decoded = msgspec.toml.decode(data, type=model)
            # logger.info(f"Loaded TOML: {filepath}") # Reduce spam for lazy loading
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

        # 2. Check Legacy Cache
        if filename in self.images:
            self.images.move_to_end(filename)
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

    def _lazy_loader_for_msgspec_dict(
        self, model_type: type[T], file_path: str, dict_attr_name: str
    ) -> LazyLoader:
        """
        Helper to create a LazyLoader that loads the ENTIRE TOML file when any key is accessed.
        Note: The current data structure (one big TOML file per category) doesn't support granular per-item loading well
        without refactoring the data files into 1-file-per-item directories.

        So for now, 'Lazy' means we defer the parsing of the big file until the first access of ANY item in it.
        """

        def loader(key: str) -> Any:
            # This loader is slightly hacky: It loads everything on first miss, populates the ENTIRE cache,
            # and returns the requested key.
            # If the file hasn't been loaded yet, load it now.
            # But LazyLoader logic expects load_func to return ONE item.

            # Alternative Lazy Strategy for Monolithic Files:
            # We can't really load *just* "Reimu" from "yukkuris.toml" easily without parsing the whole thing.
            # So we stick to: Load the Whole File On First Access.

            logger.info(f"Lazy Loading File: {file_path}")
            data_obj = self.load_toml_model(file_path, model_type)
            if data_obj:
                # We have the data. We should populate the cache of the LazyLoader with ALL items.
                # However, we are inside the loader function which only knows to return one value.
                # We can access the lazy loader instance if we used a method, but here we are in a closure.

                # Use a small trick: The LazyLoader's cache is exposed.
                # But we don't have reference to 'self.yukkuri_types' here yet.
                pass

            return None  # Placeholder, logic below is better

        # Refined Logic:
        # Since our data is currently in big files (e.g. types.toml), "Lazy Loading" just means "Don't parse types.toml at startup".
        # We can implement a specialized LazyLoader that replaces itself with the real dict on first access?

        pass

    def load_all_data(self) -> None:
        """
        Sets up LazyLoaders for game data.
        """
        # Since we use Monolithic TOMLs, true per-item lazy loading isn't possible,
        # but we can defer the file read until first access.

        # We define a lambda that loads the file and returns the dict.
        # But our attributes (self.yukkuri_types) expect to BE the dict.

        # NOTE: Implementing full LazyLoader requires granular files or a smarter LazyProxy.
        # given the task constraint, let's assume we want to defer the *parse*.

        # Standard load is fast enough for small files, but let's implement the pattern.
        # actually, msgspec is very fast.
        # Detailed Implementation:
        # We will use the LazyLoader to wrap the ACCESS.
        # But since we have big files, we'll just defer the whole file load.

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
            initializer=lambda: self._load_monolithic("items/items.toml", ItemData, "items"),
        )

        self.ai_actions = LazyLoader(
            load_function=lambda k: self._load_monolithic(
                "ai/actions.toml", AIData, "actions", k
            ),
            initializer=lambda: self._load_monolithic("ai/actions.toml", AIData, "actions"),
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

        # Skip load if already populated (check if mapping is not empty?)
        # For LazyLoader logic, forcing a reload is fine here as it's triggered by initializer or miss.
        
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
