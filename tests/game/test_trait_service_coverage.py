import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
from yukkuri_game.game.trait_service import TraitService

class TestTraitService:
    @pytest.fixture
    def mock_toml_data(self):
        return {
            "traits": {
                "Predator": {
                    "ai_modifiers": {
                        "hunt_desire": 1.5,
                        "fear": 0.5
                    }
                },
                "Lazy": {
                    "ai_modifiers": {
                        "sleep_desire": 2.0,
                        "hunt_desire": 0.5
                    }
                }
            },
            "interaction": {
                "Greet": {
                    "base_impact": 5.0,
                    "type": "social"
                }
            }
        }

    def test_load_data(self):
        # Mock os.path.exists and tomllib.load
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=b"")), \
             patch('yukkuri_game.game.trait_service.tomllib.load') as mock_load:

            # Setup mock return values for multiple calls
            mock_load.side_effect = [
                {"traits": {"A": 1}}, # traits.toml
                {"interaction": {"B": 2}} # interactions.toml
            ]

            service = TraitService()

            assert "A" in service.traits
            assert "B" in service.interactions
            assert len(service.traits) == 1
            assert len(service.interactions) == 1

    def test_load_data_file_not_found(self):
        with patch('os.path.exists', return_value=False):
            service = TraitService()
            assert service.traits == {}
            assert service.interactions == {}

    def test_load_data_exception(self):
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yukkuri_game.game.trait_service.tomllib.load', side_effect=Exception("Error")):

            service = TraitService()
            assert service.traits == {}
            assert service.interactions == {}

    def test_get_trait(self, mock_toml_data):
        service = TraitService()
        service.traits = mock_toml_data["traits"]

        assert service.get_trait("Predator") is not None
        assert service.get_trait("Unknown") is None

    def test_get_interaction(self, mock_toml_data):
        service = TraitService()
        service.interactions = mock_toml_data["interaction"]

        assert service.get_interaction("Greet") is not None
        assert service.get_interaction("Unknown") is None

    def test_get_all_trait_ids(self, mock_toml_data):
        service = TraitService()
        service.traits = mock_toml_data["traits"]

        ids = service.get_all_trait_ids()
        assert "Predator" in ids
        assert "Lazy" in ids
        assert len(ids) == 2

    def test_calculate_overrides(self, mock_toml_data):
        service = TraitService()
        service.traits = mock_toml_data["traits"]

        # Single trait
        overrides = service.calculate_overrides({"Predator"})
        assert overrides["hunt_desire"] == 1.5
        assert overrides["fear"] == 0.5

        # Multiple traits (Lazy overrides Predator's hunt_desire if loaded last)
        # Note: Set order is not guaranteed, so result might vary if we rely on order.
        # But TraitService iterates set.
        # Let's test non-conflicting first.

        # Actually, let's test specific override logic.
        # If set iteration order matters, then result is unstable.
        # But for now we just verify it combines them.

        overrides = service.calculate_overrides({"Predator", "Lazy"})

        assert "sleep_desire" in overrides
        assert "fear" in overrides
        assert "hunt_desire" in overrides

        # Verify one of the values is taken
        assert overrides["hunt_desire"] in [1.5, 0.5]
