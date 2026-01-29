import math
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.yukkuri_components import YukkuriStats, AIState


def test_manual_override_prevents_utility_switch(game_driver: GameDriver):
    """
    Verify that manual_override prevents UtilitySelector from changing the action,
    and that the override is cleared after the action completes.
    """
    driver = game_driver
    driver.setup()

    # Create a yukkuri and a target item
    start_pos = (100, 100)
    target_pos = (200, 100)
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    item_id = driver.create_item("cookie", *target_pos)

    # Set AI to Eat the item manually
    driver.set_ai_action(yukkuri_id, "Eat", target_id=item_id)

    # Verify manual override is set
    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai.manual_override is True
    assert ai.current_action == "Eat"

    # Run for a bit and verify action doesn't change even if other needs are high
    # Force high energy to discourage Sleep (if it was an option) but also
    # force full hunger to discourage Eat normally?
    # Actually, UtilitySelector checks needs. If we are full, utility for Eat is low.
    from yukkuri_game.game.yukkuri_components import Needs
    needs = driver.world.get_component(yukkuri_id, Needs)
    if needs:
        needs.hunger = 0  # Full, so Eat utility should be low
        needs.energy = 100

    driver.run_for(seconds=0.2)

    # Action should still be Eat because of override
    assert ai.current_action == "Eat"
    assert ai.manual_override is True

    # Check if it moved
    current_pos = driver.get_transform(yukkuri_id)
    dist_traveled = math.hypot(current_pos.x - 100, current_pos.y - 100)
    assert dist_traveled > 0, "Should have moved towards cookie"

    # Now let it finish eating
    # 500 distance / 100 speed = 5 seconds. Plus interaction time.
    driver.run_for(seconds=10.0)

    # Check if item exists (debug)
    # from yukkuri_game.game.components import ItemStats
    item_remains = driver.world.entity_exists(item_id)
    assert not item_remains, "Item should have been eaten"

    # After finishing, manual_override should be cleared
    assert ai.manual_override is False, (
        f"Manual override should be cleared. Item exists? {item_remains}. Action: {ai.current_action}."
    )

    # And AI should have picked a new action (likely Idle or Wander)
    # Since hunger is 0 and energy 100, probably Wander.
    # However, if Utility logic prefers Eat (score 0 vs 0), we check that target is cleared.
    if ai.current_action == "Eat":
        assert ai.current_target_id == -1, "Eat action persisted but target was not cleared"
    else:
        assert ai.current_action != "Eat"
