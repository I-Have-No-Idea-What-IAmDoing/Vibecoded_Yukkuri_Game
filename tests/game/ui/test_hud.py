import pytest
from unittest.mock import MagicMock, patch
import pygame
import pygame_gui
from pygame_gui.core.interfaces import IContainerLikeInterface
from yukkuri_game.game.ui.hud import HUD
from yukkuri_game.game.ui.hud_events import HudEvents
from yukkuri_game.game.ui.hud_layout import HudLayout
from yukkuri_game.game.ui.hud_renderer import HudRenderer
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService, TimeService, InputService, PersistenceService
from yukkuri_game.game.settings_service import SettingsService
from yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats, EmotionalState
from yukkuri_game.game.events import PlacementStartedEvent, TogglePauseRequest, CycleSpeedRequest, TrainEntityRequest, SellEntityRequest, LogMessageEvent, ResolutionChangedEvent

@pytest.fixture
def mock_ui_manager():
    return MagicMock(spec=pygame_gui.UIManager)

@pytest.fixture
def mock_services():
    """
    Returns a dictionary of singleton mock services to be used by mock_world.
    """
    economy = MagicMock(spec=EconomyService)
    economy.get_money.return_value = 1000

    time_svc = MagicMock(spec=TimeService)
    time_svc.time_elapsed = 125.0

    input_svc = MagicMock(spec=InputService)
    input_svc.hovered_entity_id = -1
    input_svc.hovered_entity_pos = (0, 0)
    input_svc.is_dragging = False
    input_svc.drag_start_pos = (0, 0)
    input_svc.drag_current_pos = (10, 10)

    settings = MagicMock(spec=SettingsService)
    persistence = MagicMock(spec=PersistenceService)

    return {
        EconomyService: economy,
        TimeService: time_svc,
        InputService: input_svc,
        SettingsService: settings,
        PersistenceService: persistence
    }

@pytest.fixture
def mock_world(mock_services):
    world = MagicMock(spec=World)
    services = MagicMock()
    world.services = services

    # Mock services retrieval to return singletons
    def get_service(service_type):
        return mock_services.get(service_type, MagicMock())

    services.get.side_effect = get_service
    services.try_get.side_effect = get_service

    return world

@pytest.fixture
def mock_event_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def hud_layout(mock_ui_manager):
    # Mock UIPanel to adhere to IContainerLikeInterface
    MockPanel = MagicMock(spec=IContainerLikeInterface)
    with patch('yukkuri_game.game.ui.hud_layout.UIPanel', return_value=MockPanel), \
         patch('yukkuri_game.game.ui.hud_layout.UILabel'), \
         patch('yukkuri_game.game.ui.hud_layout.UIButton'), \
         patch('yukkuri_game.game.ui.hud_layout.UITextBox'):
        layout = HudLayout(mock_ui_manager, 800, 600)
    return layout

@pytest.fixture
def hud_events(hud_layout, mock_world, mock_event_bus):
    # HudEvents takes (layout, world, event_bus)
    return HudEvents(hud_layout, mock_world, mock_event_bus)

@pytest.fixture
def hud_renderer(hud_layout, mock_world):
    # HudRenderer takes (layout, world)
    return HudRenderer(hud_layout, mock_world)

class TestHudLayout:
    def test_init(self, mock_ui_manager):
        MockPanel = MagicMock(spec=IContainerLikeInterface)

        with patch('yukkuri_game.game.ui.hud_layout.UIPanel', return_value=MockPanel) as MockPanelCls, \
             patch('yukkuri_game.game.ui.hud_layout.UILabel') as MockLabel, \
             patch('yukkuri_game.game.ui.hud_layout.UIButton') as MockButton, \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox') as MockTextBox:

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
        with patch('yukkuri_game.game.ui.hud_layout.UIWindow', spec=True) as MockWindow, \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox', spec=True) as MockTextBox, \
             patch('yukkuri_game.game.ui.hud_layout.UIButton', spec=True) as MockButton, \
             patch('yukkuri_game.game.ui.hud_layout.UIScrollingContainer', spec=True) as MockScrollingContainer:

            hud_layout.create_selection_window(has_stats=True)

            assert hud_layout.selection_window is not None
            assert hud_layout.info_scroll_container is not None
            assert hud_layout.info_label is not None
            assert hud_layout.sell_btn is not None
            assert hud_layout.train_btn is not None

    def test_create_selection_window_no_stats(self, hud_layout, mock_ui_manager):
        with patch('yukkuri_game.game.ui.hud_layout.UIWindow', spec=True), \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox', spec=True), \
             patch('yukkuri_game.game.ui.hud_layout.UIButton', spec=True), \
             patch('yukkuri_game.game.ui.hud_layout.UIScrollingContainer', spec=True):

            hud_layout.create_selection_window(has_stats=False)

            assert hud_layout.sell_btn is None
            assert hud_layout.train_btn is None

    def test_close_selection_window(self, hud_layout):
        mock_window = MagicMock()
        hud_layout.selection_window = mock_window

        hud_layout.close_selection_window()

        mock_window.kill.assert_called_once()
        assert hud_layout.selection_window is None

    def test_create_debug_window(self, hud_layout, mock_ui_manager):
        with patch('yukkuri_game.game.ui.hud_layout.UIWindow') as MockWindow, \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox') as MockTextBox:

            hud_layout.create_debug_window()

            assert hud_layout.debug_window is not None
            assert hud_layout.debug_text_box is not None

    def test_resize(self, hud_layout):
        with patch.object(hud_layout, 'rebuild_ui') as mock_rebuild:
            hud_layout.resize(1920, 1080)
            assert hud_layout.width == 1920
            assert hud_layout.height == 1080
            mock_rebuild.assert_called_once()

class TestHudEvents:
    def test_process_event_save(self, hud_events, hud_layout, mock_world):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.save_btn

        assert hud_events.process_event(event) is True
        mock_world.services.try_get(PersistenceService).save_game.assert_called_once()

    def test_process_event_load(self, hud_events, hud_layout, mock_world):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        # Make sure objects are identical/comparable
        hud_layout.load_btn = MagicMock()
        event.ui_element = hud_layout.load_btn

        assert hud_events.process_event(event) is True
        mock_world.services.try_get(PersistenceService).load_game.assert_called_once()

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

    def test_process_event_buy_reimu(self, hud_events, hud_layout, mock_world, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED

        reimu_btn = MagicMock()
        hud_layout.buy_buttons = {reimu_btn: {"type_id": "reimu", "cost": 100, "category": "yukkuri", "name": "Reimu"}}

        event.ui_element = reimu_btn
        # Set money
        mock_world.services.get(EconomyService).get_money.return_value = 200

        assert hud_events.process_event(event) is True
        # Verify event published
        assert mock_event_bus.publish.called
        args, _ = mock_event_bus.publish.call_args
        assert isinstance(args[0], PlacementStartedEvent)
        # PlacementStartedEvent(type_id, cost, entity_type)
        # HudEvents calls: PlacementStartedEvent("reimu", 100, "yukkuri")
        assert args[0].type_id == "reimu"
        assert args[0].entity_type == "yukkuri"

    def test_process_event_buy_reimu_insufficient_funds(self, hud_events, hud_layout, mock_world, mock_event_bus):
        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED

        reimu_btn = MagicMock()
        hud_layout.buy_buttons = {reimu_btn: {"type_id": "reimu", "cost": 100, "category": "yukkuri", "name": "Reimu"}}

        event.ui_element = reimu_btn
        # Set money
        mock_world.services.get(EconomyService).get_money.return_value = 50

        assert hud_events.process_event(event) is True # Handled, but no action
        mock_event_bus.publish.assert_not_called()

    def test_process_event_sell_entity(self, hud_events, hud_layout, mock_event_bus):
        # Setup selection window elements
        hud_layout.selection_window = MagicMock()
        hud_layout.sell_btn = MagicMock()

        hud_events.selected_entities = [123]

        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.sell_btn

        assert hud_events.process_event(event) is True
        # Check that SellEntityRequest was published
        mock_event_bus.publish.assert_called_with(SellEntityRequest(123))

    def test_process_event_train_entity(self, hud_events, hud_layout, mock_event_bus):
        # Setup selection window elements
        hud_layout.selection_window = MagicMock()
        hud_layout.train_btn = MagicMock()

        hud_events.selected_entities = [123]

        event = MagicMock()
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = hud_layout.train_btn

        assert hud_events.process_event(event) is True
        # Check that TrainEntityRequest was published
        mock_event_bus.publish.assert_called_with(TrainEntityRequest(123))

    def test_apply_window_settings_publishes_event(self, hud_events, mock_event_bus):
        with patch('pygame.display.set_mode') as mock_set_mode:
            hud_events._apply_window_settings(1024, 768, True)
            mock_set_mode.assert_called_with((1024, 768), pygame.RESIZABLE | pygame.FULLSCREEN)
            mock_event_bus.publish.assert_called_with(ResolutionChangedEvent(1024, 768, True))

class TestHudRenderer:
    def test_update_top_bar(self, hud_renderer, hud_layout, mock_world):
        hud_layout.money_label = MagicMock()
        hud_layout.time_label = MagicMock()

        # Update mock values
        mock_world.services.get(EconomyService).get_money.return_value = 1000
        mock_world.services.try_get(TimeService).time_elapsed = 125.0

        # Patch UITextBox as well since it's used for hover tooltip now
        with patch('yukkuri_game.game.ui.hud_layout.UIPanel'), \
             patch('yukkuri_game.game.ui.hud_layout.UILabel'), \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox'):
            hud_renderer.update(0.1, [], False)

        hud_layout.money_label.set_text.assert_called_with("Money: $1000")
        # 125 sec = 2 min 5 sec
        hud_layout.time_label.set_text.assert_called_with("Time: 02:05")

    def test_update_selection_yukkuri(self, hud_renderer, hud_layout, mock_world):
        hud_layout.selection_window = MagicMock()
        hud_layout.info_label = MagicMock()

        # Fix TypeError: YukkuriStats missing arguments
        stats = YukkuriStats(name="TestReimu", type_id="reimu")
        stats.hunger = 50.0
        stats.health = 70.0
        stats.badges = 3 # Badges is an int

        emo = EmotionalState()
        emo.happiness = 60.0

        ai = AIState()
        ai.current_action = "Eating"

        def get_comp(e, t):
            if t == YukkuriStats: return stats
            if t == AIState: return ai
            if t == EmotionalState: return emo
            return None

        mock_world.get_component.side_effect = get_comp
        mock_world.has_component.side_effect = lambda e, t: t == YukkuriStats

        with patch('yukkuri_game.game.ui.hud_layout.UIPanel'), \
             patch('yukkuri_game.game.ui.hud_layout.UILabel'), \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox'):
            hud_renderer.update(0.1, [1], False)

        assert hud_layout.info_label.set_text.called
        text = hud_layout.info_label.set_text.call_args[0][0]
        assert "TestReimu" in text
        assert "Eating" in text
        assert "<b>Badges:</b> 3" in text
        # assert "Gold" in text # We removed Gold badge logic from test setup as badges is int

    def test_update_selection_item(self, hud_renderer, hud_layout, mock_world):
        hud_layout.selection_window = MagicMock()
        hud_layout.info_label = MagicMock()

        # Fix TypeError: ItemStats missing arguments
        item_stats = ItemStats(name="Cookie", type_id="cookie", cost=10)

        # Mock get_component to return None for YukkuriStats and item_stats for ItemStats
        def get_comp(ent, comp_type):
            if comp_type == YukkuriStats: return None
            if comp_type == ItemStats: return item_stats
            return None

        mock_world.get_component.side_effect = get_comp
        mock_world.has_component.side_effect = lambda e, t: t == ItemStats

        with patch('yukkuri_game.game.ui.hud_layout.UIPanel'), \
             patch('yukkuri_game.game.ui.hud_layout.UILabel'), \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox'):
            hud_renderer.update(0.1, [1], False)

        assert hud_layout.info_label.set_text.called
        text = hud_layout.info_label.set_text.call_args[0][0]
        assert "Cookie" in text
        assert "10" in text

    def test_update_debug_window(self, hud_renderer, hud_layout, mock_world):
        hud_layout.debug_window = MagicMock()
        hud_layout.debug_text_box = MagicMock()
        # mock_world._entities = {1, 2, 3} # Private attribute usage
        mock_world.get_all_entities.return_value = [1, 2, 3]
        hud_renderer.fps = 60.0

        mock_world.services.get(EconomyService).get_money.return_value = 1000

        with patch('yukkuri_game.game.ui.hud_layout.UIPanel'), \
             patch('yukkuri_game.game.ui.hud_layout.UILabel'), \
             patch('yukkuri_game.game.ui.hud_layout.UITextBox'):
            hud_renderer.update(0.1, [], True)

        assert hud_layout.debug_text_box.set_text.called
        text = hud_layout.debug_text_box.set_text.call_args[0][0]
        # Fix comparison logic or text expectation
        # "<b>FPS:</b> {self.fps:.2f}<br>..."
        assert "<b>FPS:</b> 60.00" in text
        assert "<b>Entities:</b> 3" in text

    def test_show_error(self, hud_renderer, hud_layout):
        with patch('yukkuri_game.game.ui.hud_renderer.UIMessageWindow') as MockMsgWindow:
            hud_renderer.show_error("Something went wrong")
            MockMsgWindow.assert_called_once()
