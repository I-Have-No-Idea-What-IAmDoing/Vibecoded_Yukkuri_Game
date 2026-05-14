import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pygame_gui
from pygame_gui.core.interfaces import IContainerLikeInterface
from yukkuri_game.game.ui.hud_events import HudEvents
from yukkuri_game.game.ui.hud_layout import HudLayout
from yukkuri_game.game.ui.hud_renderer import HudRenderer
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import YukkuriStats, Needs, AIState, ItemStats
from yukkuri_game.game.events import (
    PlacementStartedEvent,
    TogglePauseRequest,
    CycleSpeedRequest,
    TrainEntityRequest,
    SellEntityRequest,
    ResolutionChangedEvent,
    SaveGameRequest,
    LoadGameRequest,
)
from yukkuri_game.game.services import EconomyService, TimeService
from yukkuri_game.game.save_manager import SaveManager


@pytest.fixture
def mock_ui_manager():
    return MagicMock(spec=pygame_gui.UIManager)


@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)

    # Mock services
    services = MagicMock()
    world.services = services

    input_service = MagicMock()
    input_service.hovered_entity_id = -1
    input_service.hovered_entity_pos = (0, 0)
    input_service.is_dragging = False
    input_service.drag_start_pos = (0, 0)
    input_service.drag_current_pos = (10, 10)

    economy_service = MagicMock(spec=EconomyService)
    type(economy_service).money = PropertyMock(return_value=1000)

    time_service = MagicMock(spec=TimeService)
    time_service.time_elapsed = 125  # 2 min 5 sec
    time_service.time_of_day = 12.0  # Noon
    time_service.hour_of_day = 12.0  # Noon (alias)
    time_service.game_speed = 1.0  # Normal speed
    time_service.day = 1  # Day 1

    save_manager = MagicMock(spec=SaveManager)

    # Setup services.try_get logic
    def try_get(service_type):
        if service_type == EconomyService:
            return economy_service
        if service_type == TimeService:
            return time_service
        if service_type == SaveManager:
            return save_manager
        return None

    # Setup services.get logic
    def get(service_type):
        if service_type == EconomyService:
            return economy_service
        if service_type == TimeService:
            return time_service
        if service_type == SaveManager:
            return save_manager
        return MagicMock()

    services.try_get.side_effect = try_get
    services.get.side_effect = get
    services.input_service = input_service  # Accessed as property sometimes? No, usually services.get(InputService)

    return world


@pytest.fixture
def mock_event_bus():
    return MagicMock(spec=EventBus)


@pytest.fixture
def hud_layout(mock_ui_manager):
    # Mock UIPanel to adhere to IContainerLikeInterface
    MockPanel = MagicMock(spec=IContainerLikeInterface)
    MockPanel.kill = MagicMock()  # Needs kill

    # Mock UIScrollingContainer
    MockScrollingContainer = MagicMock(spec=IContainerLikeInterface)
    MockScrollingContainer.set_scrollable_area_dimensions = MagicMock()

    with (
        patch("yukkuri_game.game.ui.hud_layout.UIPanel", return_value=MockPanel),
        patch("yukkuri_game.game.ui.hud_layout.UILabel"),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIButton",
            side_effect=lambda *args, **kwargs: MagicMock(),
        ),
        patch("yukkuri_game.game.ui.hud_layout.UITextBox"),
        patch(
            "yukkuri_game.game.ui.hud_layout.UIScrollingContainer",
            return_value=MockScrollingContainer,
        ),
    ):
        layout = HudLayout(mock_ui_manager, 800, 600)
    return layout


@pytest.fixture
def hud_events(hud_layout, mock_world, mock_event_bus):
    # HUD uses world instead of game_manager now
    return HudEvents(hud_layout, mock_world, mock_event_bus)


@pytest.fixture
def hud_renderer(hud_layout, mock_world):
    # HUD uses world instead of game_manager now
    return HudRenderer(hud_layout, mock_world)


class TestHudLayout:
    def test_init(self, mock_ui_manager):
        MockPanel = MagicMock(spec=IContainerLikeInterface)
        MockScrollingContainer = MagicMock(spec=IContainerLikeInterface)
        MockScrollingContainer.set_scrollable_area_dimensions = MagicMock()

        with (
            patch("yukkuri_game.game.ui.hud_layout.UIPanel", return_value=MockPanel),
            patch("yukkuri_game.game.ui.hud_layout.UILabel"),
            patch(
                "yukkuri_game.game.ui.hud_layout.UIButton",
                side_effect=lambda *args, **kwargs: MagicMock(),
            ),
            patch("yukkuri_game.game.ui.hud_layout.UITextBox"),
            patch(
                "yukkuri_game.game.ui.hud_layout.UIScrollingContainer",
                return_value=MockScrollingContainer,
            ),
        ):
            layout = HudLayout(mock_ui_manager, 800, 600)

            assert layout.width == 800
            assert layout.height == 600
            assert layout.top_panel is not None
            assert layout.bottom_panel is not None

            # Check if critical buttons were created
            assert layout.save_btn is not None
            assert layout.load_btn is not None
            assert layout.log_box is not None

    def test_create_selection_window(self, hud_layout, mock_ui_manager):
        # We need to mock EntityInfoPanel and its show method to avoid Pygame GUI internals
        with patch("yukkuri_game.game.ui.hud_layout.EntityInfoPanel"):
            hud_layout.create_selection_window(has_stats=True)

            assert hud_layout.entity_info_panel is not None
            hud_layout.entity_info_panel.show.assert_called_once()

    def test_create_selection_window_no_stats(self, hud_layout, mock_ui_manager):
        with patch("yukkuri_game.game.ui.hud_layout.EntityInfoPanel"):
            hud_layout.create_selection_window(has_stats=False)

            assert hud_layout.entity_info_panel is not None
            hud_layout.entity_info_panel.show.assert_called_once()

    def test_close_selection_window(self, hud_layout):
        # Capture the mock before it gets cleared
        mock_panel = MagicMock()
        hud_layout.entity_info_panel = mock_panel

        hud_layout.close_selection_window()

        mock_panel.close.assert_called_once()
        assert hud_layout.entity_info_panel is None

    def test_create_debug_window(self, hud_layout, mock_ui_manager):
        with (
            patch("yukkuri_game.game.ui.hud_layout.UIWindow"),
            patch("yukkuri_game.game.ui.hud_layout.UITextBox"),
        ):
            hud_layout.create_debug_window()

            assert hud_layout.debug_window is not None
            assert hud_layout.debug_text_box is not None

    def test_resize(self, hud_layout):
        with patch.object(hud_layout, "rebuild_ui") as mock_rebuild:
            hud_layout.resize(1920, 1080)
            assert hud_layout.width == 1920
            assert hud_layout.height == 1080
            mock_rebuild.assert_called_once()


class TestHudEvents:
    def test_process_event_save(self, hud_events, hud_layout, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.save_btn

        assert hud_events.process_event(event) is True
        # Check event published instead of direct service call
        mock_event_bus.publish.assert_called_with(SaveGameRequest("savegame"))

    def test_process_event_load(self, hud_events, hud_layout, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        # Make sure objects are identical/comparable
        hud_layout.load_btn = MagicMock()
        event.ui_element = hud_layout.load_btn

        assert hud_events.process_event(event) is True
        mock_event_bus.publish.assert_called_with(LoadGameRequest("savegame"))

    def test_process_event_pause(self, hud_events, hud_layout, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        hud_layout.pause_btn = MagicMock()
        event.ui_element = hud_layout.pause_btn

        assert hud_events.process_event(event) is True
        # Check that TogglePauseRequest was published
        mock_event_bus.publish.assert_called_with(TogglePauseRequest())

    def test_process_event_speed(self, hud_events, hud_layout, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        hud_layout.speed_btn = MagicMock()
        event.ui_element = hud_layout.speed_btn

        assert hud_events.process_event(event) is True
        # Check that CycleSpeedRequest was published
        mock_event_bus.publish.assert_called_with(CycleSpeedRequest())

    def test_process_event_buy_reimu(
        self, hud_events, hud_layout, mock_world, mock_event_bus
    ):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED

        reimu_btn = MagicMock()
        hud_layout.buy_buttons = {
            reimu_btn: {
                "type_id": "reimu",
                "cost": 100,
                "category": "yukkuri",
                "name": "Reimu",
            }
        }

        event.ui_element = reimu_btn
        # mock_world already set up with 1000 money

        assert hud_events.process_event(event) is True
        # Verify event published
        assert mock_event_bus.publish.called
        args, _ = mock_event_bus.publish.call_args
        assert isinstance(args[0], PlacementStartedEvent)
        # PlacementStartedEvent(type_id, cost, entity_type)
        # HudEvents calls: PlacementStartedEvent("reimu", 100, "yukkuri")
        assert args[0].type_id == "reimu"
        assert args[0].entity_type == "yukkuri"

    def test_process_event_buy_reimu_insufficient_funds(
        self, hud_events, hud_layout, mock_world, mock_event_bus
    ):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED

        reimu_btn = MagicMock()
        hud_layout.buy_buttons = {
            reimu_btn: {
                "type_id": "reimu",
                "cost": 100,
                "category": "yukkuri",
                "name": "Reimu",
            }
        }

        event.ui_element = reimu_btn

        # Override money return value
        economy = mock_world.services.get(EconomyService)
        type(economy).money = PropertyMock(return_value=50)

        assert hud_events.process_event(event) is True  # Handled, but no action
        mock_event_bus.publish.assert_not_called()

    def test_process_event_sell_entity(self, hud_events, hud_layout, mock_event_bus):
        # Setup selection window elements indirectly via entity_info_panel
        hud_layout.entity_info_panel = MagicMock()
        hud_layout.entity_info_panel.sell_btn = MagicMock()


        hud_events.selected_entities = [123]

        # 1. Click Sell Button
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.entity_info_panel.sell_btn

        # Mock UIConfirmationDialog to avoid real instantiation issues in test
        with patch("yukkuri_game.game.ui.hud_events.UIConfirmationDialog") as MockDialog:
            mock_dialog_instance = MockDialog.return_value

            assert hud_events.process_event(event) is True

            # Verify Dialog was created
            MockDialog.assert_called_once()
            assert hud_events.confirmation_dialog == mock_dialog_instance
            assert hud_events.pending_sell_entities == [123]

            # Verify SellEntityRequest was NOT yet published
            mock_event_bus.publish.assert_not_called()

            # 2. Confirm the Dialog
            confirm_event = MagicMock()
            confirm_event.type = pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED
            confirm_event.ui_element = mock_dialog_instance

            assert hud_events.process_event(confirm_event) is True

            # Verify SellEntityRequest WAS published
            mock_event_bus.publish.assert_called_with(SellEntityRequest(123))

            # Verify cleanup
            assert hud_events.confirmation_dialog is None
            assert hud_events.pending_sell_entities == []

    def test_process_event_train_entity(self, hud_events, hud_layout, mock_event_bus):
        # Setup selection window elements
        hud_layout.entity_info_panel = MagicMock()
        hud_layout.entity_info_panel.train_btn = MagicMock()

        hud_events.selected_entities = [123]

        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.entity_info_panel.train_btn

        assert hud_events.process_event(event) is True
        # Check that TrainEntityRequest was published
        mock_event_bus.publish.assert_called_with(TrainEntityRequest(123))

    def test_apply_window_settings_publishes_event(self, hud_events, mock_event_bus):
        # We assume pygame.display.set_mode is NOT called by HudEvents anymore
        hud_events._apply_window_settings(1024, 768, True)
        mock_event_bus.publish.assert_called_with(
            ResolutionChangedEvent(1024, 768, True)
        )


class TestHudRenderer:
    def test_update_top_bar(self, hud_renderer, hud_layout):
        hud_layout.money_label = MagicMock()
        hud_layout.time_label = MagicMock()

        # Patch UITextBox as well since it's used for hover tooltip now
        with (
            patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
            patch("yukkuri_game.game.ui.hud_layout.UILabel"),
            patch("yukkuri_game.game.ui.hud_layout.UITextBox"),
            patch("yukkuri_game.game.ui.hud_layout.NonBlockingTextBox"),  # Added
        ):
            hud_renderer.update(0.1, [], False)

        hud_layout.money_label.set_text.assert_called_with("Money: $1000")
        # Day 1 at 12:00 (noon)
        hud_layout.time_label.set_text.assert_called_with("Day 1 - 12:00")

    def test_update_selection_yukkuri(self, hud_renderer, hud_layout, mock_world):
        hud_layout.entity_info_panel = MagicMock()

        # Fix TypeError: YukkuriStats missing arguments
        stats = YukkuriStats(name="TestReimu", type_id="reimu", badges=3, age=0.0)
        needs = Needs(health=70.0, max_health=100.0, hunger=50.0)

        ai = AIState()
        ai.current_action = "Eating"

        def get_comp(ent, comp_type):
            if comp_type == YukkuriStats:
                return stats
            if comp_type == Needs:
                return needs
            if comp_type == AIState:
                return ai
            return None

        mock_world.try_get_component.side_effect = get_comp
        mock_world.has_component.side_effect = lambda e, t: t == YukkuriStats

        hud_renderer.update(0.1, [1], False)

        # It calls update_stats now, not update_info
        assert hud_layout.entity_info_panel.update_stats.called
        # Check args passed to update_stats (single string argument)
        args = hud_layout.entity_info_panel.update_stats.call_args[0]
        assert "TestReimu" in args[0]
        assert (
            "Eating" in args[0]
        )  # current_action passed as description? check implementation

    def test_update_selection_item(self, hud_renderer, hud_layout, mock_world):
        hud_layout.entity_info_panel = MagicMock()

        # Fix TypeError: ItemStats missing arguments
        item_stats = ItemStats(name="Cookie", type_id="cookie", cost=10)

        # Mock get_component to return None for YukkuriStats and item_stats for ItemStats
        def get_comp(ent, comp_type):
            if comp_type == YukkuriStats:
                return None
            if comp_type == ItemStats:
                return item_stats
            return None

        mock_world.try_get_component.side_effect = get_comp
        mock_world.has_component.side_effect = lambda e, t: t == ItemStats

        hud_renderer.update(0.1, [1], False)

        assert hud_layout.entity_info_panel.update_stats.called
        args = hud_layout.entity_info_panel.update_stats.call_args[0]
        assert "Cookie" in args[0]

    def test_update_debug_window(self, hud_renderer, hud_layout, mock_world):
        hud_layout.debug_window = MagicMock()
        hud_layout.debug_text_box = MagicMock()
        mock_world._entities = {1, 2, 3}
        mock_world.get_all_entities.return_value = [1, 2, 3]
        hud_renderer.fps = 60.0

        with (
            patch("yukkuri_game.game.ui.hud_layout.UIPanel"),
            patch("yukkuri_game.game.ui.hud_layout.UILabel"),
            patch("yukkuri_game.game.ui.hud_layout.UITextBox"),
        ):
            hud_renderer.update(0.1, [], True)

        assert hud_layout.debug_text_box.set_text.called
        text = hud_layout.debug_text_box.set_text.call_args[0][0]
        assert "<b>FPS:</b> 60.00" in text
        assert "<b>Entities:</b> 3" in text

    def test_show_error(self, hud_renderer, hud_layout):
        with patch(
            "yukkuri_game.game.ui.hud_renderer.UIMessageWindow"
        ) as MockMsgWindow:
            hud_renderer.show_error("Something went wrong")
            MockMsgWindow.assert_called_once()
