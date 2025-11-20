import os
import tomllib
import pygame
from loguru import logger
from typing import Any, Dict

class ResourceManager:
    """
    Manages game resources such as images, sounds, and configuration files.

    Attributes:
        data_dir (str): The directory containing data files (TOML).
        assets_dir (str): The directory containing asset files (images, sounds).
        images (Dict[str, pygame.Surface]): A cache of loaded images.
        sounds (Dict[str, pygame.mixer.Sound]): A cache of loaded sounds.
        configs (Dict[str, Any]): A cache of loaded configurations.
        yukkuri_types (Dict[str, Any]): Loaded Yukkuri type definitions.
        item_types (Dict[str, Any]): Loaded Item type definitions.
        ai_actions (Dict[str, Any]): Loaded AI action definitions.
    """

    def __init__(self, data_dir: str = "data", assets_dir: str = "assets"):
        """
        Initializes the ResourceManager.

        Args:
            data_dir: The directory path for data files. Defaults to "data".
            assets_dir: The directory path for asset files. Defaults to "assets".
        """
        self.data_dir = data_dir
        self.assets_dir = assets_dir
        self.images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.configs: Dict[str, Any] = {}

        # Cache for loaded data
        self.yukkuri_types = {}
        self.item_types = {}
        self.ai_actions = {}

    def load_toml(self, filepath: str) -> Dict[str, Any]:
        """
        Loads a TOML file relative to the data directory.

        Args:
            filepath: The relative path to the TOML file within the data directory.

        Returns:
            Dict[str, Any]: The parsed TOML data, or an empty dictionary if loading fails.
        """
        full_path = os.path.join(self.data_dir, filepath)
        try:
            with open(full_path, "rb") as f:
                data = tomllib.load(f)
            logger.info(f"Loaded TOML: {filepath}")
            return data
        except Exception as e:
            logger.error(f"Failed to load TOML {filepath}: {e}")
            return {}

    def load_image(self, filename: str) -> pygame.Surface:
        """
        Loads an image relative to the assets/images directory.

        If the image is already loaded, it returns the cached surface.
        If the file is missing, a placeholder surface is returned.

        Args:
            filename: The filename of the image to load.

        Returns:
            pygame.Surface: The loaded image surface or a placeholder.
        """
        if filename in self.images:
            return self.images[filename]

        full_path = os.path.join(self.assets_dir, "images", filename)
        try:
            # Check if file exists, if not create a placeholder
            if not os.path.exists(full_path):
                logger.warning(f"Image not found: {filename}. Creating placeholder.")
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255)) # Magenta placeholder
                self.images[filename] = surf
                return surf

            img = pygame.image.load(full_path).convert_alpha()
            self.images[filename] = img
            return img
        except Exception as e:
            logger.error(f"Failed to load image {filename}: {e}")
            surf = pygame.Surface((32, 32))
            surf.fill((255, 0, 0))
            return surf

    def load_all_data(self) -> None:
        """
        Loads all core game data from the data directory.

        This includes Yukkuri types, Item types, and AI actions.
        """
        # Load Yukkuri Types
        yukkuri_data = self.load_toml("yukkuris/types.toml")
        self.yukkuri_types = yukkuri_data.get("yukkuris", {})

        # Load Items
        item_data = self.load_toml("items/items.toml")
        self.item_types = item_data.get("items", {})

        # Load AI Actions
        ai_data = self.load_toml("ai/actions.toml")
        self.ai_actions = ai_data.get("actions", {})

        logger.info("All data loaded.")
