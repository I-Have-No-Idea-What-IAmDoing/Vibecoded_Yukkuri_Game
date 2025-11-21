import msgspec
from pathlib import Path

class WorldSettings(msgspec.Struct):
    width: int = 3000
    height: int = 3000

class ConfigFile(msgspec.Struct):
    world: WorldSettings = msgspec.field(default_factory=WorldSettings)

class StatDecaySettings(msgspec.Struct):
    hunger: float = 2.0
    happiness: float = 0.5
    energy: float = 0.5
    cleanliness: float = 0.2
    age: float = 1.0

class RulesFile(msgspec.Struct):
    stat_decay: StatDecaySettings = msgspec.field(default_factory=StatDecaySettings)

class GameConfig(msgspec.Struct):
    world: WorldSettings
    rules: RulesFile

def load_config(data_dir: Path = Path("data")) -> GameConfig:
    """
    Loads configuration from TOML files in the specified directory.

    Args:
        data_dir: The directory containing config.toml and rules.toml.

    Returns:
        GameConfig: The loaded configuration.

    Raises:
        msgspec.ValidationError: If the configuration files contain invalid types.
    """
    config_path = data_dir / "config.toml"
    rules_path = data_dir / "rules.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            config_file = msgspec.toml.decode(f.read(), type=ConfigFile)
    else:
        config_file = ConfigFile()

    if rules_path.exists():
        with open(rules_path, "rb") as f:
            rules_file = msgspec.toml.decode(f.read(), type=RulesFile)
    else:
        rules_file = RulesFile()

    return GameConfig(world=config_file.world, rules=rules_file)
