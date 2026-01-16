import pytest
from unittest.mock import MagicMock, patch, mock_open
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import GoalType


class TestEntityFactoryLoader:
    @pytest.fixture
    def factory(self):
        world = MagicMock(spec=World)
        return EntityFactory(world)

    def test_load_archetype_success(self, factory):
        toml_content = b"""
        archetype_id = "test_arch"
        stamina_regen = 15.0
        
        [priorities]
        list = ["EAT", "SLEEP"]
        
        [prey_tags]
        tags = ["Bug"]
        
        [predator_tags]
        tags = ["Bird"]
        
        [personality_bias]
        kindness = 10.0
        """

        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                config = factory.load_archetype("test_arch")

                assert config is not None
                assert config.archetype_id == "test_arch"
                assert config.stamina_regen == 15.0
                assert config.priorities == [GoalType.EAT, GoalType.SLEEP]
                assert "Bug" in config.prey_tags
                assert "Bird" in config.predator_tags
                assert config.personality_bias["kindness"] == 10.0

    def test_load_archetype_not_found(self, factory):
        with patch("pathlib.Path.exists", return_value=False):
            config = factory.load_archetype("non_existent")
            assert config is None
