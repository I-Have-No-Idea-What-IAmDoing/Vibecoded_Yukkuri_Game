from test_utils import make_configured_world
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.components import YukkuriStats, Needs, EmotionalState
from yukkuri_game.config import StatDecaySettings


def test_starvation_decay():
    from yukkuri_game.engine.services.time_service import TimeService
    settings = StatDecaySettings(starvation_damage=10.0)
    world = make_configured_world(stat_decay_settings=settings)
    
    # Set time scale to 1.0
    world.services.get(TimeService).scale = 1.0
    
    system = EmotionSystem()
    world.add_system(system)

    # Create a Yukkuri entity
    entity = world.create_entity()

    # Initialize stats with max hunger (starving)
    stats = YukkuriStats(name="TestYukkuri", type_id="test", age=0.0)

    needs = Needs(
        max_health=100.0,
        health=100.0,
        hunger=100.0,  # Starving
        energy=50.0,
        cleanliness=50.0,
    )

    emotional = EmotionalState(happiness=50.0)

    world.add_component(entity, stats)
    world.add_component(entity, needs)
    world.add_component(entity, emotional)

    # Run simulation for 1 second
    dt = 1.0
    # Throttled system needs to be updated directly if world.update(dt) doesn't run enough loops
    # but EmotionSystem uses world.time for its own throttling.
    system.update(world, dt)

    # Check if health has decreased
    # Expected: 100 - 10 * 1 = 90
    assert needs.health < 100.0
    assert needs.health == 90.0


def test_no_decay_when_not_starving():
    from yukkuri_game.engine.services.time_service import TimeService
    settings = StatDecaySettings(starvation_damage=10.0)
    world = make_configured_world(stat_decay_settings=settings)
    
    # Set time scale to 1.0
    world.services.get(TimeService).scale = 1.0
    
    system = EmotionSystem()
    world.add_system(system)

    entity = world.create_entity()

    # Initialize stats with high hunger but not starving
    stats = YukkuriStats(name="TestYukkuri", type_id="test", age=0.0)

    needs = Needs(
        max_health=100.0,
        health=100.0,
        hunger=90.0,  # Not starving
        energy=50.0,
        cleanliness=50.0,
    )
    emotional = EmotionalState(happiness=50.0)

    world.add_component(entity, stats)
    world.add_component(entity, needs)
    world.add_component(entity, emotional)

    dt = 1.0
    system.update(world, dt)

    assert needs.health == 100.0
