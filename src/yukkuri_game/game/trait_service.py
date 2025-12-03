"""
Module for managing personality traits and social interaction definitions.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager
from ..engine.data_models import TraitDefinition, InteractionDefinition


class TraitService:
    """
    Service responsible for loading and providing access to Personality Traits and Interaction definitions.

    Attributes:
        world (Optional[World]): The ECS world instance.
        traits (Dict[str, TraitDefinition]): Loaded trait data.
        interactions (Dict[str, InteractionDefinition]): Loaded interaction data.
    """

    def __init__(self, world: Optional[World] = None):
        """
        Initializes the TraitService.

        Args:
            world (Optional[World]): The ECS World instance.
        """
        self.world = world
        self.traits: Dict[str, TraitDefinition] = {}
        self.interactions: Dict[str, InteractionDefinition] = {}

        self.load_data()

    def load_data(self) -> None:
        """
        Loads trait and interaction data from ResourceManager.

        Returns:
            None
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

    def get_trait(self, trait_id: str) -> Optional[TraitDefinition]:
        """
        Returns the data for a specific trait.

        Args:
            trait_id (str): The ID of the trait to retrieve.

        Returns:
            Optional[TraitDefinition]: The trait definition, or None if not found.
        """
        return self.traits.get(trait_id)

    def get_interaction(self, interaction_id: str) -> Optional[InteractionDefinition]:
        """
        Returns the data for a specific interaction.

        Args:
            interaction_id (str): The ID of the interaction to retrieve.

        Returns:
            Optional[InteractionDefinition]: The interaction definition, or None if not found.
        """
        return self.interactions.get(interaction_id)

    def get_all_trait_ids(self) -> List[str]:
        """
        Returns a list of all available trait IDs.

        Returns:
            List[str]: A list of trait IDs.
        """
        return list(self.traits.keys())

    def calculate_overrides(self, traits: set[str]) -> Dict[str, Any]:
        """
        Calculates the effective AI modifiers for a set of traits.
        Merges conflicting modifiers (last one wins currently).

        Args:
            traits (set[str]): A set of trait IDs to calculate overrides for.

        Returns:
            Dict[str, Any]: A dictionary of AI consideration overrides.
        """
        overrides = {}
        for trait_id in traits:
            trait_data = self.get_trait(trait_id)
            if trait_data:
                # Use attribute access for msgspec Struct
                if trait_data.ai_modifiers:
                    for cons_name, mod in trait_data.ai_modifiers.items():
                        overrides[cons_name] = mod
        return overrides
