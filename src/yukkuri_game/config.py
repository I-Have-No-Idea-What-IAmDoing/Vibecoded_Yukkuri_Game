"""
Module for loading and managing game configuration.

This module defines the configuration structures for the game, including
world settings, rule settings (stats, lifecycle, social, skills), and
the main configuration loader.
"""

import msgspec
from pathlib import Path


class TimeSettings(msgspec.Struct):
    """
    Configuration settings for the game time system.

    Attributes:
        scale (float): Game seconds per physics second (default 60x = 1 min/sec).
        day_start_hour (float): Hour when day begins (0-24).
        night_start_hour (float): Hour when night begins (0-24).
    """

    scale: float = 60.0
    day_start_hour: float = 6.0
    night_start_hour: float = 20.0


class WorldSettings(msgspec.Struct):
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


class ConfigFile(msgspec.Struct):
    """
    Represents the structure of the main config.toml file.

    Attributes:
        world (WorldSettings): The world configuration settings.
        time (TimeSettings): The time system configuration settings.
    """

    world: WorldSettings = msgspec.field(default_factory=WorldSettings)
    time: TimeSettings = msgspec.field(default_factory=TimeSettings)


class StatDecaySettings(msgspec.Struct):
    """
    Configuration settings for stat decay rates.

    Attributes:
        hunger (float): Decay rate for hunger per tick or unit time.
        happiness (float): Decay rate for happiness per tick or unit time.
        stress (float): Decay rate for stress per tick or unit time.
        energy (float): Decay rate for energy per tick or unit time.
        cleanliness (float): Decay rate for cleanliness per tick or unit time.
        social (float): Decay rate for social needs per tick or unit time.
        age (float): Decay rate for age (or growth rate) per tick or unit time.
        starvation_damage (float): Damage taken per tick when starving.
        personality_drift_rate (float): Rate at which personality traits can drift over time.
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


class LifecycleSettings(msgspec.Struct):
    """
    Configuration settings for lifecycle events (birth, growth, death).

    Attributes:
        baby_age_threshold (float): Age threshold until a yukkuri stops being a baby.
        child_age_threshold (float): Age threshold until a yukkuri stops being a child.
        breeding_happiness_threshold (float): Minimum happiness required to breed.
        breeding_energy_threshold (float): Minimum energy required to breed.
        breeding_cost (float): Energy cost incurred during breeding.
        breeding_chance (float): Probability of breeding per tick if conditions are met.
    """

    baby_age_threshold: float = 100.0
    child_age_threshold: float = 300.0
    breeding_happiness_threshold: float = 80.0
    breeding_energy_threshold: float = 80.0
    breeding_cost: float = 50.0
    breeding_chance: float = 0.001


class SocialSettings(msgspec.Struct):
    """
    Configuration for the social system.

    Attributes:
        memory_importance_threshold (float): Threshold for a memory to be considered important.
        max_gossip_length (int): Maximum length of gossip chains (number of participants).
        witness_threshold (float): Distance threshold for witnessing events.
    """

    memory_importance_threshold: float = 50.0
    max_gossip_length: int = 10
    witness_threshold: float = 5.0


class SkillsSettings(msgspec.Struct):
    """
    Configuration for the skill system.

    Attributes:
        xp_base (float): Base XP required for level up.
        xp_exponent (float): Exponent for XP scaling with level.
    """

    xp_base: float = 100.0
    xp_exponent: float = 1.5


class StatsSettings(msgspec.Struct):
    """
    Configuration for calculating yukkuri stats and value.

    Attributes:
        badge_value (int): Monetary value assigned to each badge type.
        health_deficit_penalty (float): Value penalty multiplier per missing health point.
        age_value_bonus (float): Value bonus per minute of age.
        intelligence_base (float): Base intelligence multiplier for stats.
    """

    badge_value: int = 500
    health_deficit_penalty: float = 2.0
    age_value_bonus: float = 10.0
    intelligence_base: float = 0.5


class RulesFile(msgspec.Struct):
    """
    Represents the structure of the rules.toml file.

    Attributes:
        stat_decay (StatDecaySettings): The stat decay configuration.
        lifecycle (LifecycleSettings): The lifecycle configuration.
        social (SocialSettings): The social system configuration.
        skills (SkillsSettings): The skill system configuration.
        stats (StatsSettings): The general stats configuration.
    """

    stat_decay: StatDecaySettings = msgspec.field(default_factory=StatDecaySettings)
    lifecycle: LifecycleSettings = msgspec.field(default_factory=LifecycleSettings)
    social: SocialSettings = msgspec.field(default_factory=SocialSettings)
    skills: SkillsSettings = msgspec.field(default_factory=SkillsSettings)
    stats: StatsSettings = msgspec.field(default_factory=StatsSettings)


class GameConfig(msgspec.Struct):
    """
    Combined configuration for the game.

    Attributes:
        world (WorldSettings): World settings loaded from config.toml.
        time (TimeSettings): Time settings loaded from config.toml.
        rules (RulesFile): Game rules loaded from rules.toml.
    """

    world: WorldSettings
    time: TimeSettings
    rules: RulesFile


def load_config(data_dir: Path = Path("data")) -> GameConfig:
    """
    Loads configuration from TOML files in the specified directory.

    It looks for 'config.toml' and 'rules.toml' in the given directory.
    If the files do not exist, default configurations are used.

    Args:
        data_dir (Path): The directory containing config.toml and rules.toml.
                         Defaults to 'data'.

    Returns:
        GameConfig: The loaded game configuration object.

    Raises:
        msgspec.ValidationError: If the configuration files contain invalid types or structures.
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

    return GameConfig(world=config_file.world, time=config_file.time, rules=rules_file)
