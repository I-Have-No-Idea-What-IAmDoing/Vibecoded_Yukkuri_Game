import os
import sys

# For now we use the built-in tomllib for loading.
# If performance becomes an issue or we need validation, we can switch to msgspec/pydantic.
if sys.version_info >= (3, 11):
    import tomllib
else:
    # Fallback for older python, though project says >= 3.11
    try:
        import tomli as tomllib
    except ImportError:
        import tomllib

from typing import Dict, Any, List, Optional
from loguru import logger
from ..engine.ecs import World

class TraitService:
    """
    Service responsible for loading and providing access to Personality Traits and Interaction definitions.
    """

    def __init__(self, world: Optional[World] = None):
        self.world = world
        self.traits: Dict[str, Any] = {}
        self.interactions: Dict[str, Any] = {}
        self.data_dir = os.path.join("data") # Base data directory

        self.load_data()

    def load_data(self):
        """Loads trait and interaction data from TOML files."""
        traits_path = os.path.join(self.data_dir, "traits", "traits.toml")
        interactions_path = os.path.join(self.data_dir, "ai", "interactions.toml")

        self.traits = self._load_toml(traits_path).get("traits", {})
        self.interactions = self._load_toml(interactions_path).get("interaction", {})

        logger.info(f"Loaded {len(self.traits)} traits and {len(self.interactions)} interactions.")

    def _load_toml(self, filepath: str) -> Dict[str, Any]:
        """Helper to load a TOML file safely."""
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return {}
        try:
            with open(filepath, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            return {}

    def get_trait(self, trait_id: str) -> Optional[Dict[str, Any]]:
        """Returns the data for a specific trait."""
        return self.traits.get(trait_id)

    def get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Returns the data for a specific interaction."""
        return self.interactions.get(interaction_id)

    def get_all_trait_ids(self) -> List[str]:
        """Returns a list of all available trait IDs."""
        return list(self.traits.keys())

    def calculate_overrides(self, traits: set[str]) -> Dict[str, Any]:
        """
        Calculates the effective AI modifiers for a set of traits.
        Merges conflicting modifiers (last one wins currently).
        """
        overrides = {}
        for trait_id in traits:
            trait_data = self.get_trait(trait_id)
            if trait_data and "ai_modifiers" in trait_data:
                for cons_name, mod in trait_data["ai_modifiers"].items():
                    overrides[cons_name] = mod
        return overrides
