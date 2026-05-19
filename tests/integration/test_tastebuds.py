"""
Integration tests for Yukkuri spoiled tastebuds, hunger bypass, and decay.
"""

from yukkuri_game.engine.components import Transform
from yukkuri_game.game.components import EmotionalState
from yukkuri_game.game.components import InteractionRequest
from yukkuri_game.game.components import ItemStats
from yukkuri_game.game.components import Needs
from yukkuri_game.game.components import YukkuriStats
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.systems.hunger_system import HungerSystem
from yukkuri_game.testing.driver import GameDriver


def test_tastebuds_flow(game_driver: GameDriver) -> None:
    """
    Verify spoiled tastebuds threshold, scaled happiness, hunger bypass,
    and decay.
    """
    driver = game_driver
    driver.setup()

    # 1. Spawn a reimu Yukkuri and check default tastebud_spoiled is 0.0
    yukkuri_id = driver.create_yukkuri("reimu", 100, 100)
    stats = driver.get_component(yukkuri_id, YukkuriStats)
    needs = driver.get_component(yukkuri_id, Needs)
    emotional = driver.get_component(yukkuri_id, EmotionalState)

    assert stats is not None
    assert needs is not None
    assert emotional is not None
    assert stats.tastebud_spoiled == 0.0

    # 2. Spawn a standard cookie and premium super_cookie
    # standard cookie: quality = 10, fun = 10, nutrition = 20
    # premium super_cookie: quality = 50, fun = 30, nutrition = 50
    cookie_id = driver.create_item("cookie", 105, 105)
    super_cookie_id = driver.create_item("super_cookie", 105, 105)

    cookie_stats = driver.get_component(cookie_id, ItemStats)
    super_stats = driver.get_component(super_cookie_id, ItemStats)

    assert cookie_stats is not None
    assert super_stats is not None
    assert cookie_stats.quality == 10.0
    assert super_stats.quality == 50.0

    # 3. Eat premium super_cookie first when full
    needs.hunger = 0.0
    emotional.happiness = 50.0

    system = HungerSystem()
    request = InteractionRequest(target_id=super_cookie_id, consume=True)

    result = system.process_consumption(
        driver.world,
        yukkuri_id,
        request,
        Transform(x=100, y=100),
        super_cookie_id,
        super_stats,
    )

    assert result is True
    # Verify tastebud_spoiled updated to 50.0 (premium quality)
    assert stats.tastebud_spoiled == 50.0
    # Verify we got full happiness gain (+30) because we had
    # no spoiled tastebuds
    assert emotional.happiness == 80.0

    # 4. Eat a standard cookie when full (hunger = 0.0) -> Scaled happiness!
    # Expected multiplier = 10.0 / 50.0 = 0.2
    # Expected happiness gain = 10.0 * 0.2 = 2.0
    emotional.happiness = 50.0
    needs.hunger = 0.0

    request_cookie = InteractionRequest(target_id=cookie_id, consume=True)
    result_cookie = system.process_consumption(
        driver.world,
        yukkuri_id,
        request_cookie,
        Transform(x=100, y=100),
        cookie_id,
        cookie_stats,
    )

    assert result_cookie is True
    # Happiness should be 50.0 + 2.0 = 52.0
    assert emotional.happiness == 52.0

    # 5. Hunger Bypass: Spawn another cookie and eat when
    # starving (hunger = 80.0)
    # At hunger >= 80.0, hunger bypass factor should be 1.0 (multiplier = 1.0)
    # Expected happiness gain = full 10.0
    cookie2_id = driver.create_item("cookie", 105, 105)
    cookie2_stats = driver.get_component(cookie2_id, ItemStats)
    assert cookie2_stats is not None

    needs.hunger = 80.0
    emotional.happiness = 50.0

    request_cookie2 = InteractionRequest(target_id=cookie2_id, consume=True)
    result_cookie2 = system.process_consumption(
        driver.world,
        yukkuri_id,
        request_cookie2,
        Transform(x=100, y=100),
        cookie2_id,
        cookie2_stats,
    )

    assert result_cookie2 is True
    # Happiness should be 50.0 + 10.0 = 60.0 (full happiness gain!)
    assert emotional.happiness == 60.0

    # 6. Tastebud spoiled decay over time
    # Check that in EmotionSystem, the spoiled tastebuds decay.
    # We will simulate 1000 game seconds.
    # At decay rate of 0.001 per game second, spoiled should decay by 1.0
    assert stats.tastebud_spoiled == 50.0

    emotion_sys = EmotionSystem()
    emotion_sys.ecs_world = driver.world
    emotion_sys.initialize()

    # Simulate 1000 game seconds
    # With time_scale=60.0 (default), 1 physics second = 60 game seconds
    # 1000 game seconds / 60 = 16.666 physics seconds
    driver.run_for(seconds=17.0)

    # tastebud_spoiled should have decayed towards 0
    assert stats.tastebud_spoiled < 50.0
