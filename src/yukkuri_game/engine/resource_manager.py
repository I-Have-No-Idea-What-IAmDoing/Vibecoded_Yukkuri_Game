"""
Module for managing game resources like images, sounds, and data files.
"""

import os
from typing import Any, Dict, Type, TypeVar, Optional

import msgspec
import pygame
from loguru import logger

from .data_models import (
    YukkuriData, ItemData, AIData, YukkuriType, ItemType, AIAction, GameTuning,
    SkillData, SkillDefinition, TraitData, TraitDefinition, InteractionData, InteractionDefinition
)

T = TypeVar("T")

class ResourceManager:
    """
    Manages game resources such as images, sounds, and configuration files.

    Attributes:
        data_dir (str): The directory containing data files (TOML).
        assets_dir (str): The directory containing asset files (images, sounds).
        images (Dict[str, pygame.Surface]): A cache of loaded images.
        sounds (Dict[str, pygame.mixer.Sound]): A cache of loaded sounds.
        configs (Dict[str, Any]): A cache of loaded configurations.
        yukkuri_types (Dict[str, YukkuriType]): Loaded Yukkuri type definitions.
        item_types (Dict[str, ItemType]): Loaded Item type definitions.
        ai_actions (Dict[str, AIAction]): Loaded AI action definitions.
        tuning (Optional[GameTuning]): Loaded game tuning parameters.
        skills (Dict[str, SkillDefinition]): Loaded skill definitions.
        traits (Dict[str, TraitDefinition]): Loaded trait definitions.
        interactions (Dict[str, InteractionDefinition]): Loaded interaction definitions.
    """

    def __init__(self, data_dir: str = "data", assets_dir: str = "assets"):
        """
        Initializes the ResourceManager.

        Args:
            data_dir (str): The directory path for data files. Defaults to "data".
            assets_dir (str): The directory path for asset files. Defaults to "assets".
        """
        self.data_dir = data_dir
        self.assets_dir = assets_dir
        self.images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.configs: Dict[str, Any] = {}

        # Cache for loaded data
        self.yukkuri_types: Dict[str, YukkuriType] = {}
        self.item_types: Dict[str, ItemType] = {}
        self.ai_actions: Dict[str, AIAction] = {}
        self.tuning: Optional[GameTuning] = None
        self.skills: Dict[str, SkillDefinition] = {}
        self.traits: Dict[str, TraitDefinition] = {}
        self.interactions: Dict[str, InteractionDefinition] = {}

    def load_toml_model(self, filepath: str, model: Type[T]) -> Optional[T]:
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
            with open(full_path, "rb") as f:
                data = f.read()

            # noinspection PyTypeChecker
            decoded = msgspec.toml.decode(data, type=model)
            logger.info(f"Loaded TOML: {filepath}")
            return decoded  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Failed to load TOML {filepath}: {e}")
            return None

    def load_image(self, filename: str) -> pygame.Surface:
        """
        Loads an image relative to the assets/images directory.

        If the image is already loaded, it returns the cached surface.
        If the file is missing, a placeholder surface is returned.

        Args:
            filename (str): The filename of the image to load.

        Returns:
            pygame.Surface: The loaded image surface or a placeholder.
        """
        if filename in self.images:
            return self.images[filename]

        full_path = os.path.join(self.assets_dir, "images", filename)
        try:
            if not os.path.exists(full_path):
                logger.warning(f"Image not found: {filename}. Creating placeholder.")
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255))  # Magenta placeholder
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

        This includes Yukkuri types, Item types, AI actions, and game tuning.

        Returns:
            None
        """
        # Load Yukkuri Types
        yukkuri_data = self.load_toml_model("yukkuris/types.toml", YukkuriData)
        if yukkuri_data:
            self.yukkuri_types = yukkuri_data.yukkuris
        else:
            self.yukkuri_types = {}

        # Load Items
        item_data = self.load_toml_model("items/items.toml", ItemData)
        if item_data:
            self.item_types = item_data.items
        else:
            self.item_types = {}

        # Load AI Actions
        ai_data = self.load_toml_model("ai/actions.toml", AIData)
        if ai_data:
            self.ai_actions = ai_data.actions
        else:
            self.ai_actions = {}

        # Load Game Tuning
        self.tuning = self.load_toml_model("yukkuri_tuning.toml", GameTuning)

        # Load Skills
        skill_data = self.load_toml_model("skills/skills.toml", SkillData)
        if skill_data:
            self.skills = skill_data.skills
        else:
            self.skills = {}

        # Load Traits
        trait_data = self.load_toml_model("traits/traits.toml", TraitData)
        if trait_data:
            self.traits = trait_data.traits
        else:
            self.traits = {}

        # Load Interactions
        interaction_data = self.load_toml_model("ai/interactions.toml", InteractionData)
        if interaction_data:
            self.interactions = interaction_data.interaction
        else:
            self.interactions = {}

        logger.info("All data loaded.")
