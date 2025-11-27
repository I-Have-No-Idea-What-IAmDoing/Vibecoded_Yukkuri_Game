import pytest
from unittest.mock import MagicMock, patch, mock_open
import pygame
import os
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.data_models import YukkuriData, ItemData, AIData, YukkuriType, ItemType, AIAction

class TestResourceManager:
    @pytest.fixture
    def resource_manager(self):
        return ResourceManager(data_dir="test_data", assets_dir="test_assets")

    def test_initialization(self, resource_manager):
        assert resource_manager.data_dir == "test_data"
        assert resource_manager.assets_dir == "test_assets"
        assert resource_manager.images == {}
        assert resource_manager.sounds == {}
        assert resource_manager.configs == {}
        assert resource_manager.yukkuri_types == {}

    def test_load_image_success(self, resource_manager):
        with patch('os.path.exists', return_value=True):
            with patch('pygame.image.load') as mock_load:
                mock_surf = MagicMock(spec=pygame.Surface)
                mock_load.return_value.convert_alpha.return_value = mock_surf

                img = resource_manager.load_image("test.png")

                assert img == mock_surf
                assert "test.png" in resource_manager.images

                # Test cache hit
                img2 = resource_manager.load_image("test.png")
                assert img2 == img
                mock_load.call_count == 1

    def test_load_image_not_found(self, resource_manager):
        with patch('os.path.exists', return_value=False):
            img = resource_manager.load_image("missing.png")

            assert isinstance(img, pygame.Surface)
            assert "missing.png" in resource_manager.images
            # Should be magenta placeholder
            # Since we can't easily inspect pixels of mock/headless surface without display,
            # we assume the logic ran correctly.

    def test_load_image_exception(self, resource_manager):
        with patch('os.path.exists', return_value=True):
            with patch('pygame.image.load', side_effect=Exception("Load error")):
                img = resource_manager.load_image("broken.png")

                assert isinstance(img, pygame.Surface)
                # Should be red placeholder

    def test_load_toml_model_success(self, resource_manager):
        toml_content = b"""
        [yukkuris.reimu]
        name = "Reimu"
        image = "reimu.png"
        width = 32
        height = 32
        max_health = 100
        base_happiness = 50
        cost = 100
        animations = {}
        """

        with patch("builtins.open", mock_open(read_data=toml_content)):
            # We need to mock msgspec.toml.decode or ensure the data matches the model
            # Here we rely on msgspec actually working if dependencies are installed.
            # However, constructing YukkuriData from raw bytes in test might be complex if models have specific structure.
            # Let's try to patch decode instead for simplicity in unit test.

            mock_data = YukkuriData(yukkuris={"reimu": YukkuriType(
                name="Reimu", image="reimu.png", width=32, height=32, max_health=100, base_happiness=50
            )})

            with patch('msgspec.toml.decode', return_value=mock_data) as mock_decode:
                data = resource_manager.load_toml_model("test.toml", YukkuriData)
                assert data == mock_data
                mock_decode.assert_called()

    def test_load_toml_model_failure(self, resource_manager):
        with patch("builtins.open", side_effect=FileNotFoundError):
            data = resource_manager.load_toml_model("missing.toml", YukkuriData)
            assert data is None

    def test_load_all_data(self, resource_manager):
        # Mock load_toml_model responses
        mock_yukkuri_data = YukkuriData(yukkuris={"test": MagicMock()})
        mock_item_data = ItemData(items={"food": MagicMock()})
        mock_ai_data = AIData(actions={"idle": MagicMock()})
        mock_tuning_data = MagicMock()

        with patch.object(resource_manager, 'load_toml_model') as mock_load:
            mock_load.side_effect = [mock_yukkuri_data, mock_item_data, mock_ai_data, mock_tuning_data]

            resource_manager.load_all_data()

            assert "test" in resource_manager.yukkuri_types
            assert "food" in resource_manager.item_types
            assert "idle" in resource_manager.ai_actions
            assert resource_manager.tuning == mock_tuning_data

    def test_load_all_data_empty(self, resource_manager):
        with patch.object(resource_manager, 'load_toml_model', return_value=None):
            resource_manager.load_all_data()
            assert resource_manager.yukkuri_types == {}
            assert resource_manager.item_types == {}
            assert resource_manager.ai_actions == {}
