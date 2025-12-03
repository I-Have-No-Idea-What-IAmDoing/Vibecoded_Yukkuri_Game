
import os
import pytest
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.data_models import YukkuriData

def test_load_animations_from_toml():
    # Setup ResourceManager with test data directory
    # We assume the test is running from the root, so tests/data is the relative path
    # However, ResourceManager assumes 'data_dir' structure.
    # Our file is at tests/data/yukkuris/types_with_animation.toml

    rm = ResourceManager(data_dir="tests/data")

    # We can use load_toml_model directly to test parsing
    yukkuri_data = rm.load_toml_model("yukkuris/types_with_animation.toml", YukkuriData)

    assert yukkuri_data is not None
    assert "test_yukkuri" in yukkuri_data.yukkuris

    yukkuri_type = yukkuri_data.yukkuris["test_yukkuri"]
    assert yukkuri_type.name == "Test Yukkuri"

    # Check animations
    assert len(yukkuri_type.animations) == 2
    assert "walk" in yukkuri_type.animations
    assert "idle" in yukkuri_type.animations

    walk_anim = yukkuri_type.animations["walk"]
    assert walk_anim.name == "walk"
    assert walk_anim.frames == [0, 1, 2, 3]
    assert walk_anim.frame_duration == 0.1
    assert walk_anim.loop is True

    idle_anim = yukkuri_type.animations["idle"]
    assert idle_anim.frames == [0]
