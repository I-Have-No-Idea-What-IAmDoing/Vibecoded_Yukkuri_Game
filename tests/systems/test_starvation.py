
import sys
import os
import pytest

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.stat_decay import StatDecaySystem
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.config import StatDecaySettings

def test_starvation_decay():
    world = World()
    settings = StatDecaySettings(starvation_damage=10.0)
    system = StatDecaySystem(settings)
    world.add_system(system)

    # Create a Yukkuri entity
    entity = world.create_entity()

    # Initialize stats with max hunger (starving)
    stats = YukkuriStats(
        name="TestYukkuri",
        type_id="test",
        max_health=100.0,
        health=100.0,
        hunger=100.0, # Starving
        happiness=50.0,
        energy=50.0,
        cleanliness=50.0,
        age=0.0
    )

    world.add_component(entity, stats)

    # Run simulation for 1 second
    dt = 1.0
    world.update(dt)

    # Check if health has decreased
    # Expected: 100 - 10 * 1 = 90
    assert stats.health < 100.0
    assert stats.health == 90.0

def test_no_decay_when_not_starving():
    world = World()
    settings = StatDecaySettings(starvation_damage=10.0)
    system = StatDecaySystem(settings)
    world.add_system(system)

    entity = world.create_entity()

    # Initialize stats with high hunger but not starving
    stats = YukkuriStats(
        name="TestYukkuri",
        type_id="test",
        max_health=100.0,
        health=100.0,
        hunger=90.0, # Lower starting hunger to ensure we don't hit 100 immediately
        happiness=50.0,
        energy=50.0,
        cleanliness=50.0,
        age=0.0
    )

    world.add_component(entity, stats)

    dt = 1.0
    world.update(dt)

    assert stats.health == 100.0
