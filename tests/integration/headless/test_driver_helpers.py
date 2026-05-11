import pytest
from unittest.mock import MagicMock
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.game.components import YukkuriStats
from yukkuri_game.engine.event_bus import Event

# Note: game_driver fixture comes from conftest.py

class MockEventA(Event):
    pass

class MockEventB(Event):
    pass

def test_get_component_and_assert(game_driver: GameDriver):
    """Verifies get_component and assert_component helpers."""
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)

    # Spawn a Yukkuri
    eid = driver.create_yukkuri("reimu", 100, 100)
    assert eid != -1

    # 1. Test get_component success
    stats = driver.get_component(eid, YukkuriStats)
    assert stats is not None
    assert isinstance(stats, YukkuriStats)

    # 2. Test get_component failure (wrong type or non-existent entity)
    # Define a dummy class for something it won't have
    class DummyComponent:
        pass
    
    assert driver.get_component(eid, DummyComponent) is None  # type: ignore
    assert driver.get_component(99999, YukkuriStats) is None

    # 3. Test assert_component pass
    # Yukkuri starts with intelligence > 0 usually
    driver.assert_component(eid, YukkuriStats, lambda s: s.intelligence > 0)

    # 4. Test assert_component failure
    with pytest.raises(AssertionError, match="Assertion failed for YukkuriStats on entity"):
        driver.assert_component(eid, YukkuriStats, lambda s: s.intelligence < 0)

    with pytest.raises(AssertionError, match="does not have component DummyComponent"):
        driver.assert_component(eid, DummyComponent, lambda s: True)  # type: ignore

def test_event_bus_helpers(game_driver: GameDriver):
    """Verifies get_events and assert_event_published helpers."""
    driver = game_driver
    driver.wait_until_scene(GameplayScene)

    if not hasattr(driver.game, "event_manager"):
        pytest.skip("Game lacks event_manager")

    bus = driver.game.event_manager.bus

    # Emulate publishing events
    event_a1 = MockEventA()
    event_a2 = MockEventA()
    event_b1 = MockEventB()

    bus.publish(event_a1)
    bus.publish(event_a2)
    bus.publish(event_b1)

    # 1. Test get_events
    events_a = driver.get_events(MockEventA)
    assert len(events_a) == 2
    assert event_a1 in events_a
    assert event_a2 in events_a

    events_b = driver.get_events(MockEventB)
    assert len(events_b) == 1
    assert event_b1 in events_b

    # 2. Test assert_event_published (exists)
    driver.assert_event_published(MockEventA)
    driver.assert_event_published(MockEventB)

    # 3. Test assert_event_published (with count)
    driver.assert_event_published(MockEventA, count=2)
    driver.assert_event_published(MockEventB, count=1)

    # 4. Test assert_event_published failures
    with pytest.raises(AssertionError, match="to be published 3 times, but was 2"):
        driver.assert_event_published(MockEventA, count=3)

    class MockEventC(Event):
        pass

    with pytest.raises(AssertionError, match="was never published"):
        driver.assert_event_published(MockEventC)

def test_run_until(game_driver: GameDriver):
    """Verifies run_until wrapper."""
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)

    driver.create_yukkuri("reimu", 100, 100)

    # Record start time
    start_time = driver.simulated_time

    # Run until time advances by at least 1.0 second
    driver.run_until(lambda: driver.simulated_time >= start_time + 1.0, timeout=2.0)

    # Verify time advanced properly
    assert driver.simulated_time >= start_time + 1.0
