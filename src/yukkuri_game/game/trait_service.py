import tomllib
import os
from typing import Dict, Any, Optional

class TraitService:
    """
    Service to load, validate, and cache personality traits and interactions.
    """
    def __init__(self, data_path: str = "data"):
        self.data_path = data_path
        self.traits: Dict[str, Any] = {}
        self.interactions: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self):
        """Loads traits and interactions from TOML files."""
        traits_path = os.path.join(self.data_path, "traits", "traits.toml")
        interactions_path = os.path.join(self.data_path, "ai", "interactions.toml")

        if os.path.exists(traits_path):
            with open(traits_path, "rb") as f:
                data = tomllib.load(f)
                self.traits = data.get("traits", {})

        if os.path.exists(interactions_path):
            with open(interactions_path, "rb") as f:
                data = tomllib.load(f)
                self.interactions = data.get("interaction", {})

    def get_trait(self, trait_id: str) -> Optional[Dict[str, Any]]:
        return self.traits.get(trait_id)

    def get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        return self.interactions.get(interaction_id)

    def get_all_traits(self) -> Dict[str, Any]:
        return self.traits
