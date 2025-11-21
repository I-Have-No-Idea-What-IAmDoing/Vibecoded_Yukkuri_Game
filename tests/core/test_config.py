import pytest
import msgspec
from pathlib import Path
from yukkuri_game.config import load_config, WorldSettings, GameConfig, ConfigFile

def test_load_config_defaults(tmp_path):
    """Test loading configuration with missing files returns defaults."""
    config = load_config(tmp_path)

    assert isinstance(config, GameConfig)
    assert config.world.width == 3000
    assert config.world.height == 3000
    assert config.rules.stat_decay.hunger == 2.0
    assert config.rules.stat_decay.happiness == 0.5

def test_load_config_values(tmp_path):
    """Test loading configuration from files."""
    config_file = tmp_path / "config.toml"
    with open(config_file, "w") as f:
        f.write("[world]\nwidth = 5000\nheight = 5000\n")

    rules_file = tmp_path / "rules.toml"
    with open(rules_file, "w") as f:
        f.write("[stat_decay]\nhunger = 5.0\n")

    config = load_config(tmp_path)

    assert config.world.width == 5000
    assert config.world.height == 5000
    assert config.rules.stat_decay.hunger == 5.0
    # Check default values are preserved for missing fields if struct allows
    # msgspec structs don't partial update from file easily unless defined as Optional or we rely on the fact that we decode the whole file.
    # If the file only has `hunger`, other fields in `stat_decay` table might be missing.
    # TOML decoding to a Struct requires all required fields or default values.
    # Our structs have defaults, so omitted fields use defaults.
    assert config.rules.stat_decay.happiness == 0.5

def test_load_config_invalid_types(tmp_path):
    """Test that invalid types raise errors."""
    config_file = tmp_path / "config.toml"
    with open(config_file, "w") as f:
        f.write("[world]\nwidth = \"invalid\"\n")

    with pytest.raises(msgspec.ValidationError):
        load_config(tmp_path)

def test_load_config_partial_update(tmp_path):
    """Test that we can partially update settings."""
    # Since we use default_factory in the parent structs and defaults in child structs,
    # omitting a field in TOML should use the default value.

    rules_file = tmp_path / "rules.toml"
    with open(rules_file, "w") as f:
        f.write("[stat_decay]\nhunger = 10.0\n")
        # happiness, etc are missing

    config = load_config(tmp_path)
    assert config.rules.stat_decay.hunger == 10.0
    assert config.rules.stat_decay.happiness == 0.5
