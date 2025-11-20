import os
import tomllib
import pygame
from loguru import logger
from typing import Any, Dict

class ResourceManager:
    def __init__(self, data_dir: str = "data", assets_dir: str = "assets"):
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
        """Loads a TOML file relative to data directory."""
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
        """Loads an image relative to assets/images. Returns a surface."""
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

    def load_all_data(self):
        """Loads all core game data."""
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
