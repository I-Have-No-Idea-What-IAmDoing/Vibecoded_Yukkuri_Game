"""
Module for managing personality traits and social interaction definitions.
"""

from collections.abc import MutableMapping
from typing import Any

from loguru import logger

from ..engine.data_models import InteractionDefinition, TraitDefinition
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager


class TraitService:
    """
    Service responsible for loading and providing access to Personality Traits and Interaction definitions.

    Attributes:
        world (World | None): The ECS world instance.
        traits (MutableMapping[str, TraitDefinition]): Loaded trait data.
        interactions (MutableMapping[str, InteractionDefinition]): Loaded interaction data.
    """

    def __init__(self, world: World | None = None):
        """
        Initializes the TraitService.

        Args:
            world (World | None): The ECS World instance.
        """
        self.world = world
        self.traits: MutableMapping[str, TraitDefinition] = {}
        self.interactions: MutableMapping[str, InteractionDefinition] = {}

        self.load_data()

    def load_data(self) -> None:
        """
        Loads trait and interaction data from ResourceManager.
        """
        if not self.world:
            logger.warning("TraitService initialized without World, cannot load data.")
            return

        rm = self.world.services.try_get(ResourceManager)
        if rm:
            self.traits = rm.traits
            self.interactions = rm.interactions
        else:
            logger.warning("ResourceManager not found in World.")

        logger.info(
            f"Loaded {len(self.traits)} traits and {len(self.interactions)} interactions."
        )

    def get_trait(self, trait_id: str) -> TraitDefinition | None:
        """
        Returns the data for a specific trait.

        Args:
            trait_id (str): The ID of the trait to retrieve.

        Returns:
            TraitDefinition | None: The trait definition, or None if not found.
        """
        return self.traits.get(trait_id)

    def get_interaction(self, interaction_id: str) -> InteractionDefinition | None:
        """
        Returns the data for a specific interaction.

        Args:
            interaction_id (str): The ID of the interaction to retrieve.

        Returns:
            InteractionDefinition | None: The interaction definition, or None if not found.
        """
        return self.interactions.get(interaction_id)

    def get_all_trait_ids(self) -> list[str]:
        """
        Returns a list of all available trait IDs.

        Returns:
            list[str]: A list of trait IDs.
        """
        return list(self.traits.keys())

    def calculate_overrides(self, traits: set[str]) -> dict[str, Any]:
        """
        Calculates the effective AI modifiers for a set of traits.
        Merges conflicting modifiers (last one wins currently).

        Args:
            traits (set[str]): A set of trait IDs to calculate overrides for.

        Returns:
            dict[str, Any]: A dictionary of AI consideration overrides.
        """
        overrides = {}
        for trait_id in sorted(traits):
            trait_data = self.get_trait(trait_id)
            if trait_data:
                # Use attribute access for msgspec Struct
                if trait_data.ai_modifiers:
                    for cons_name, mod in trait_data.ai_modifiers.items():
                        overrides[cons_name] = mod
        return overrides
