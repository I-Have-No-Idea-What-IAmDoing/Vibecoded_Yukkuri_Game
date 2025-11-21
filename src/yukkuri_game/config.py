import msgspec
from pathlib import Path

class WorldSettings(msgspec.Struct):
    """
    Configuration settings for the game world.

    Attributes:
        width (int): The width of the world in pixels.
        height (int): The height of the world in pixels.
    """
    width: int = 3000
    height: int = 3000

class ConfigFile(msgspec.Struct):
    """
    Represents the structure of the main config.toml file.

    Attributes:
        world (WorldSettings): The world configuration settings.
    """
    world: WorldSettings = msgspec.field(default_factory=WorldSettings)

class StatDecaySettings(msgspec.Struct):
    """
    Configuration settings for stat decay rates.

    Attributes:
        hunger (float): Decay rate for hunger.
        happiness (float): Decay rate for happiness.
        energy (float): Decay rate for energy.
        cleanliness (float): Decay rate for cleanliness.
        age (float): Decay rate for age (or growth rate).
    """
    hunger: float = 2.0
    happiness: float = 0.5
    energy: float = 0.5
    cleanliness: float = 0.2
    age: float = 1.0

class RulesFile(msgspec.Struct):
    """
    Represents the structure of the rules.toml file.

    Attributes:
        stat_decay (StatDecaySettings): The stat decay configuration.
    """
    stat_decay: StatDecaySettings = msgspec.field(default_factory=StatDecaySettings)

class GameConfig(msgspec.Struct):
    """
    Combined configuration for the game.

    Attributes:
        world (WorldSettings): World settings from config.toml.
        rules (RulesFile): Game rules from rules.toml.
    """
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
