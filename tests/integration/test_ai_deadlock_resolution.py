"""Integration tests for Yukkuri AI deadlock resolution and cooldowns."""

import queue

from yukkuri_game.engine.components import LightSource
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.ai.navigation_service import PathResult
from yukkuri_game.game.components import AIState
from yukkuri_game.game.components import EmotionalState
from yukkuri_game.game.components import Needs
from yukkuri_game.testing.driver import GameDriver


def test_ai_deadlock_resolution_at_night(game_driver: GameDriver) -> None:
    """Verify that a Yukkuri seeking light at night hits a failure cooldown

    when pathfinding fails, falling back to Wander and resolving deadlock.
    """
    driver = game_driver
    driver.setup()

    # 1. Create a yukkuri
    yukkuri_id = driver.create_yukkuri("reimu", 100, 100)
    ai = driver.world.get_component(yukkuri_id, AIState)
    needs = driver.world.get_component(yukkuri_id, Needs)
    emotional = driver.world.get_component(yukkuri_id, EmotionalState)

    assert ai is not None

    # Reset needs to prevent other active behaviors (like eating, sleeping)
    if needs:
        needs.hunger = 0.0
        needs.energy = 100.0
        needs.social = 100.0
        needs.cleanliness = 100.0

    # Put time to night (Midnight) and set scale to 1.0 to prevent cooldown decay
    time_service = driver.world.services.get(TimeService)
    if time_service:
        time_service.time_elapsed = 0.0
        time_service.scale = 1.0

    # Elevate stress so SeekLight is prioritized, but below panic threshold (90)
    if emotional:
        emotional.stress = 60.0

    # Remove any default light sources to avoid shadowing our test light source
    for entity in list(driver.world.get_components(LightSource).keys()):
        driver.world.commands.remove_component(entity, LightSource)

    # Create a light source in the world so SeekLight becomes high utility
    light_id = driver.world.create_entity()
    driver.world.add_component(light_id, Transform(550, 550))
    driver.world.add_component(
        light_id, LightSource(radius=300.0, intensity=1.0)
    )

    # Apply commands queue to register component additions
    driver.world.commands.apply_all()

    # Manually update spatial system so light is indexed
    from yukkuri_game.engine.systems.spatial import SpatialSystem
    spatial_sys = driver.world.get_system(SpatialSystem)
    if spatial_sys:
        spatial_sys.update(driver.world, 0.016)

    # Ensure SeekLight becomes high utility by building context
    from yukkuri_game.game.ai.context_builder import UtilityContextBuilder
    ctx = UtilityContextBuilder.build_context(yukkuri_id, driver.world)

    # Let the simulation run so AI selects SeekLight
    driver.run_for(seconds=0.15)
    assert ai.current_action == "SeekLight"

    # Inject a failed pathfinding result into the navigation service
    nav_service = driver.world.services.get(NavigationService)
    if nav_service:
        # Clear queues
        for q in (nav_service.result_queue, nav_service.request_queue):
            try:
                while True:
                    q.get_nowait()
            except queue.Empty:
                pass
        ai.path = None
        nav_service.result_queue.put(
            PathResult(entity_id=yukkuri_id, path=[], success=False)
        )

    # Let the simulation step. SeekLight should process path failure, fail,
    # and go on cooldown.
    driver.run_for(seconds=0.15)

    # Verify SeekLight is on cooldown
    cooldowns = getattr(ai, "action_cooldowns", {})
    assert "SeekLight" in cooldowns
    assert cooldowns["SeekLight"] > driver.world.time

    # Run another tick so the UtilitySelector re-evaluates actions with the active cooldown
    driver.run_for(seconds=0.5)

    # Verify that Utility Selector has now excluded SeekLight and selected Wander
    assert ai.current_action == "Wander"
