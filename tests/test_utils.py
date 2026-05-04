"""
Shared test utility helpers for system tests.
"""
from unittest.mock import MagicMock


def make_configured_world(
    stat_decay_settings=None,
    lifecycle_settings=None,
    world_width: int = 1000,
    world_height: int = 1000,
):
    """
    Creates a World pre-loaded with mock GameConfig and EventBus services.

    This is the standard setup for unit-testing systems that now fetch their
    dependencies via initialize() rather than __init__ arguments.

    Args:
        stat_decay_settings: Optional StatDecaySettings instance.
        lifecycle_settings: Optional LifecycleSettings instance.
        world_width: World grid width for BehaviorSystem.
        world_height: World grid height for BehaviorSystem.

    Returns:
        World: Configured World instance.
    """
    from yukkuri_game.engine.ecs import World
    from yukkuri_game.engine.event_bus import EventBus
    from yukkuri_game.config import (
        GameConfig,
        StatDecaySettings,
        LifecycleSettings,
        SocialSettings,
        StatsSettings,
        SkillsSettings,
        TimeSettings,
    )

    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    config = MagicMock(spec=GameConfig)
    config.rules.stat_decay = stat_decay_settings or StatDecaySettings()
    config.rules.lifecycle = lifecycle_settings or LifecycleSettings()
    config.rules.social = SocialSettings()
    config.rules.stats = StatsSettings()
    config.rules.skills = SkillsSettings()
    config.time = TimeSettings()
    config.world.width = world_width
    config.world.height = world_height
    from yukkuri_game.game.services import TimeService
    world.services.register(TimeService(), TimeService)
    world.services.register(config, GameConfig)

    return world
