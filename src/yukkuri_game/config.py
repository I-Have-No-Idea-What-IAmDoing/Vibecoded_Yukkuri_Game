"""
Module for loading and managing game configuration.
"""
import msgspec
from pathlib import Path

class WorldSettings(msgspec.Struct): # type: ignore[misc]
    """
    Configuration settings for the game world.

    Attributes:
        width (int): The width of the world in pixels.
        height (int): The height of the world in pixels.
        grid_step_size (int): The size of the grid step for navigation.
        sector_size (float): The size of sectors for spatial partitioning.
    """
    width: int = 3000
    height: int = 3000
    grid_step_size: int = 50
    sector_size: float = 500.0

class ConfigFile(msgspec.Struct): # type: ignore[misc]
    """
    Represents the structure of the main config.toml file.

    Attributes:
        world (WorldSettings): The world configuration settings.
    """
    world: WorldSettings = msgspec.field(default_factory=WorldSettings)

class StatDecaySettings(msgspec.Struct): # type: ignore[misc]
    """
    Configuration settings for stat decay rates.

    Attributes:
        hunger (float): Decay rate for hunger.
        happiness (float): Decay rate for happiness.
        energy (float): Decay rate for energy.
        cleanliness (float): Decay rate for cleanliness.
        social (float): Decay rate for social needs.
        age (float): Decay rate for age (or growth rate).
        starvation_damage (float): Damage per tick when starving.
    """
    hunger: float = 2.0
    happiness: float = 0.5
    stress: float = 5.0
    energy: float = 0.5
    cleanliness: float = 0.2
    social: float = 0.5
    age: float = 1.0
    starvation_damage: float = 5.0
    personality_drift_rate: float = 0.1

class LifecycleSettings(msgspec.Struct): # type: ignore[misc]
    """
    Configuration settings for lifecycle events (birth, growth, death).

    Attributes:
        baby_age_threshold (float): Age until becoming a child.
        child_age_threshold (float): Age until becoming an adult.
        breeding_happiness_threshold (float): Happiness required to breed.
        breeding_energy_threshold (float): Energy required to breed.
        breeding_cost (float): Energy cost of breeding.
        breeding_chance (float): Probability of breeding per tick if conditions met.
    """
    baby_age_threshold: float = 100.0
    child_age_threshold: float = 300.0
    breeding_happiness_threshold: float = 80.0
    breeding_energy_threshold: float = 80.0
    breeding_cost: float = 50.0
    breeding_chance: float = 0.001

class SocialSettings(msgspec.Struct): # type: ignore[misc]
    """
    Configuration for social system.
    """
    memory_importance_threshold: float = 50.0
    max_gossip_length: int = 10
    witness_threshold: float = 5.0

class SkillsSettings(msgspec.Struct): # type: ignore[misc]
    """
    Configuration for skill system.
    """
    xp_base: float = 100.0
    xp_exponent: float = 1.5

class RulesFile(msgspec.Struct): # type: ignore[misc]
    """
    Represents the structure of the rules.toml file.

    Attributes:
        stat_decay (StatDecaySettings): The stat decay configuration.
        lifecycle (LifecycleSettings): The lifecycle configuration.
        social (SocialSettings): The social system configuration.
        skills (SkillsSettings): The skill system configuration.
    """
    stat_decay: StatDecaySettings = msgspec.field(default_factory=StatDecaySettings)
    lifecycle: LifecycleSettings = msgspec.field(default_factory=LifecycleSettings)
    social: SocialSettings = msgspec.field(default_factory=SocialSettings)
    skills: SkillsSettings = msgspec.field(default_factory=SkillsSettings)

class GameConfig(msgspec.Struct): # type: ignore[misc]
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
        data_dir (Path): The directory containing config.toml and rules.toml.

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
