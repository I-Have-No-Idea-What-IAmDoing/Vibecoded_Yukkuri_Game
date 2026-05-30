"""
Integration tests for Yukkuri Utility AI Introspection.
"""

from unittest.mock import MagicMock, patch
import pygame
import pygame_gui

from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent
from yukkuri_game.game.components import AIState
from yukkuri_game.game.ui.hud import HUD
from yukkuri_game.testing.driver import GameDriver


class MockTextBox:
    """Mock for pygame_gui UITextBox to capture text and HTML text."""

    def __init__(self, *args, **kwargs) -> None:
        self.html_text = kwargs.get("html_text", "")
        self.rect = pygame.Rect(0, 0, 100, 100)
        self.scroll_bar = MagicMock()
        self.scroll_bar.scrollable_height = 100
        self.scroll_bar.scroll_position = 0

    def set_text(self, text: str) -> None:
        self.html_text = text

    def append_html_text(self, text: str) -> None:
        self.html_text += text


class MockButton:
    """Mock for pygame_gui UIButton to capture selection state and text."""

    def __init__(self, *args, **kwargs) -> None:
        self.text = kwargs.get("text", "")
        self.selected = False

    def select(self) -> None:
        self.selected = True

    def unselect(self) -> None:
        self.selected = False

    def set_text(self, text: str) -> None:
        self.text = text


class MockDropDownMenu:
    """Mock for pygame_gui UIDropDownMenu to capture chosen option."""

    def __init__(self, *args, **kwargs) -> None:
        self.selected_option = kwargs.get("starting_option", "All Logs")


def test_selection_toggles_inspected_flag(game_driver: GameDriver) -> None:
    """
    Verify that selecting an entity toggles the is_inspected flag on its AIState.
    """
    driver = game_driver
    driver.setup()

    # Create two yukkuris
    y1 = driver.create_yukkuri("reimu", 100, 100)
    y2 = driver.create_yukkuri("marisa", 150, 150)

    ai1 = driver.world.get_component(y1, AIState)
    ai2 = driver.world.get_component(y2, AIState)

    assert ai1.is_inspected is False
    assert ai2.is_inspected is False

    # Mock UI classes to avoid font rendering crashes
    with (
        patch("yukkuri_game.game.ui.hud_layout.UITextBox", side_effect=MockTextBox),
        patch("yukkuri_game.game.ui.hud_layout.UIButton", side_effect=MockButton),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIDropDownMenu",
            side_effect=MockDropDownMenu,
        ),
        patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
        patch("yukkuri_game.game.ui.hud_layout.UILabel"),
        patch("yukkuri_game.game.ui.hud_layout.UIWindow"),
        patch("yukkuri_game.game.ui.hud_layout.UIScrollingContainer"),
        patch("yukkuri_game.game.ui.hud_layout.NonBlockingTextBox"),
        patch("yukkuri_game.game.ui.hud_layout.TabbedPanel"),
        patch("yukkuri_game.game.ui.hud_layout.ECSInspector"),
        patch("yukkuri_game.game.ui.entity_info_panel.UIWindow"),
        patch("yukkuri_game.game.ui.entity_info_panel.TabbedPanel"),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.SafeUIScrollingContainer"
        ),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.UITextBox",
            side_effect=MockTextBox,
        ),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.UIButton",
            side_effect=MockButton,
        ),
    ):
        ui_manager = MagicMock(spec=pygame_gui.UIManager)
        hud = HUD(ui_manager, driver.world)

        # Select y1
        driver.world.services.get(EventBus).publish(EntitySelectedEvent((y1,)))
        assert ai1.is_inspected is True
        assert ai2.is_inspected is False

        # Select y2
        driver.world.services.get(EventBus).publish(EntitySelectedEvent((y2,)))
        assert ai1.is_inspected is False
        assert ai2.is_inspected is True

        # Unselect all
        driver.world.services.get(EventBus).publish(EntitySelectedEvent(()))
        assert ai1.is_inspected is False
        assert ai2.is_inspected is False

        hud.cleanup()


def test_utility_selector_populates_telemetry(
    game_driver: GameDriver,
) -> None:
    """
    Verify that UtilitySelector conditionally populates last_utility_breakdown.
    """
    driver = game_driver
    driver.setup()

    y = driver.create_yukkuri("reimu", 100, 100)
    ai = driver.world.get_component(y, AIState)

    from yukkuri_game.game.ai.utility_selector import UtilitySelector

    selector = UtilitySelector(
        name="test_selector", entity_id=y, world=driver.world
    )
    selector.initialise()

    # By default, not inspected -> last_utility_breakdown should be None
    assert ai.is_inspected is False
    selector.update()
    assert ai.last_utility_breakdown is None

    # Inspect the entity
    ai.is_inspected = True
    selector.update()

    assert ai.last_utility_breakdown is not None
    breakdown = ai.last_utility_breakdown
    assert "active_action" in breakdown
    assert "actions" in breakdown
    assert "sorted_actions" in breakdown
    assert len(breakdown["sorted_actions"]) > 0


def test_hud_freeze_button_toggles_state(game_driver: GameDriver) -> None:
    """
    Verify that clicking the Freeze Updates button freezes and unfreezes the UI.
    """
    driver = game_driver
    driver.setup()

    y = driver.create_yukkuri("reimu", 100, 100)

    # Mock UI classes to avoid font rendering crashes
    with (
        patch("yukkuri_game.game.ui.hud_layout.UITextBox", side_effect=MockTextBox),
        patch("yukkuri_game.game.ui.hud_layout.UIButton", side_effect=MockButton),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIDropDownMenu",
            side_effect=MockDropDownMenu,
        ),
        patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
        patch("yukkuri_game.game.ui.hud_layout.UILabel"),
        patch("yukkuri_game.game.ui.hud_layout.UIWindow"),
        patch("yukkuri_game.game.ui.hud_layout.UIScrollingContainer"),
        patch("yukkuri_game.game.ui.hud_layout.NonBlockingTextBox"),
        patch("yukkuri_game.game.ui.hud_layout.TabbedPanel"),
        patch("yukkuri_game.game.ui.hud_layout.ECSInspector"),
        patch("yukkuri_game.game.ui.entity_info_panel.UIWindow"),
        patch("yukkuri_game.game.ui.entity_info_panel.TabbedPanel"),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.SafeUIScrollingContainer"
        ),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.UITextBox",
            side_effect=MockTextBox,
        ),
        patch(
            "yukkuri_game.game.ui.entity_info_panel.UIButton",
            side_effect=MockButton,
        ),
    ):
        ui_manager = MagicMock(spec=pygame_gui.UIManager)
        hud = HUD(ui_manager, driver.world)

        # Select y to instantiate selection window and EntityInfoPanel
        driver.world.services.get(EventBus).publish(EntitySelectedEvent((y,)))

        panel = hud.layout.entity_info_panel
        assert panel is not None
        assert panel.ai_freeze_btn is not None
        assert panel.is_ai_frozen is False

        # Press freeze button
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            ui_element=panel.ai_freeze_btn,
        )
        hud.process_event(event)

        assert panel.is_ai_frozen is True
        assert panel.ai_freeze_btn.text == "Updates Frozen"

        # Press freeze button again
        hud.process_event(event)

        assert panel.is_ai_frozen is False
        assert panel.ai_freeze_btn.text == "Freeze Updates"

        hud.cleanup()
