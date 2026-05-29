"""Tests for Tier D debugging improvements."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pymunk
import pytest

from yukkuri_game.engine.components import MovementController
from yukkuri_game.engine.components import PhysicsBody
from yukkuri_game.engine.components import Transform
from yukkuri_game.game.ai.utility_selector import UtilitySelector
from yukkuri_game.game.components import AIState
from yukkuri_game.game.ui.hud_renderer import HudRenderer
from yukkuri_game.testing.driver import GameDriver


def test_ai_decision_history(game_driver: GameDriver) -> None:
    """Verifies that decision history records action transitions.

    Args:
        game_driver (GameDriver): The game driver fixture.
    """
    driver = game_driver
    driver.setup()

    y = driver.create_yukkuri("reimu", 100, 100)
    ai = driver.world.get_component(y, AIState)

    selector = UtilitySelector(
        name="test_selector", entity_id=y, world=driver.world
    )
    selector.initialise()

    # Clear any initial history
    ai.decision_history.clear()

    # Make selector choose action A
    ai.is_inspected = True
    assert selector.engine is not None
    with patch.object(selector.engine, "select_action") as mock_select:
        mock_select.return_value = "Eat"
        selector.update()
        assert len(ai.decision_history) == 1
        assert ai.decision_history[0][0] == "Eat"

        # Ticking again with the same action should not record a transition
        selector.update()
        assert len(ai.decision_history) == 1

        # Now change to "Sleep"
        mock_select.return_value = "Sleep"
        selector.update()
        assert len(ai.decision_history) == 2
        assert ai.decision_history[1][0] == "Sleep"

        # Record more transitions to test the 10 limit
        for i in range(12):
            mock_select.return_value = f"Action_{i}"
            selector.update()

        # Should be capped at 10
        assert len(ai.decision_history) == 10
        # The last one should be Action_11
        assert ai.decision_history[-1][0] == "Action_11"


def test_hud_renderer_transform_physics_display(
    game_driver: GameDriver,
) -> None:
    """Verifies that HudRenderer extracts position and velocity for display.

    Args:
        game_driver (GameDriver): The game driver fixture.
    """
    driver = game_driver
    driver.setup()

    y = driver.create_yukkuri("reimu", 100, 100)

    # Let's ensure y has a Transform and MovementController
    transform = driver.world.get_component(y, Transform)
    transform.x = 123.4
    transform.y = 567.8

    mctrl = driver.world.get_component(y, MovementController)
    mctrl.current_velocity = pymunk.vec2d.Vec2d(12.3, -45.6)

    layout = MagicMock()
    layout.debug_window = None
    renderer = HudRenderer(layout, driver.world)

    renderer._update_stats_display([y])

    # Assert that update_stats was called with formatted pos/vel
    layout.entity_info_panel.update_stats.assert_called_once()
    called_text = layout.entity_info_panel.update_stats.call_args[0][0]
    assert "<b>Pos:</b> 123.4, 567.8" in called_text
    assert "<b>Vel:</b> 12.3, -45.6" in called_text


def test_hud_renderer_physics_body_fallback(game_driver: GameDriver) -> None:
    """Verifies that HudRenderer falls back to PhysicsBody for velocity.

    Args:
        game_driver (GameDriver): The game driver fixture.
    """
    driver = game_driver
    driver.setup()

    y = driver.create_yukkuri("reimu", 100, 100)

    # Remove MovementController
    driver.world.remove_component(y, MovementController)

    # Add PhysicsBody component
    body = pymunk.Body(1.0, 1.0)
    body.velocity = pymunk.vec2d.Vec2d(7.8, -9.0)
    shape = pymunk.Circle(body, 10)
    pbody = PhysicsBody(body=body, shape=shape)
    driver.world.add_component(y, pbody)

    layout = MagicMock()
    layout.debug_window = None
    renderer = HudRenderer(layout, driver.world)

    renderer._update_stats_display([y])

    layout.entity_info_panel.update_stats.assert_called_once()
    called_text = layout.entity_info_panel.update_stats.call_args[0][0]
    assert "<b>Vel:</b> 7.8, -9.0" in called_text
