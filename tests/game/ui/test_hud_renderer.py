import pytest
from unittest.mock import MagicMock, Mock
import pygame
from yukkuri_game.game.ui.hud_renderer import HudRenderer
from yukkuri_game.game.ui.hud_layout import HudLayout
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, AIState, RelationshipRegistry, Personality, EmotionalState
from yukkuri_game.game.services import InputService
from yukkuri_game.game.ui.hud_events import HudEvents

class TestHudRenderer:
    @pytest.fixture
    def mock_layout(self):
        layout = MagicMock(spec=HudLayout)
        layout.money_label = MagicMock()
        layout.time_label = MagicMock()
        layout.selection_window = MagicMock()
        layout.debug_window = MagicMock()
        layout.debug_text_box = MagicMock()
        layout.info_label = MagicMock()
        layout.info_scroll_container = MagicMock()
        layout.width = 800
        layout.height = 600
        layout.manager = MagicMock()
        return layout

    @pytest.fixture
    def mock_gm(self):
        gm = MagicMock(spec=GameManager)
        gm.money = 1000
        gm.time_elapsed = 125.0 # 2 min 5 sec
        gm.calculate_quality_score.return_value = 500
        return gm

    @pytest.fixture
    def mock_world(self):
        world = MagicMock(spec=World)
        world.services = MagicMock()
        return world

    @pytest.fixture
    def renderer(self, mock_layout, mock_gm, mock_world):
        return HudRenderer(mock_layout, mock_gm, mock_world)

    def test_update_top_bar(self, renderer, mock_layout, mock_gm):
        """Test updating the top bar labels."""
        renderer.update(0.016, [], False)

        mock_layout.money_label.set_text.assert_called_with("Money: $1000")
        mock_layout.time_label.set_text.assert_called_with("Time: 02:05")

    def test_update_selection_window_single_yukkuri(self, renderer, mock_layout, mock_world, mock_gm):
        """Test updating selection window for a single yukkuri."""
        entity_id = 1
        renderer.update(0.016, [entity_id], False)

        # Mock components
        stats = YukkuriStats(name="Marisa", type_id="marisa", health=80.0, hunger=50.0)
        emotional = EmotionalState(happiness=70.0, stress=10.0)
        ai = AIState(current_action="Sleeping")
        pers = Personality()

        mock_world.get_component.side_effect = lambda eid, comp_type: {
            YukkuriStats: stats,
            EmotionalState: emotional,
            AIState: ai,
            Personality: pers,
            RelationshipRegistry: RelationshipRegistry(),
            ItemStats: None
        }.get(comp_type)

        renderer.update(0.016, [entity_id], False)

        assert mock_layout.info_label.set_text.called
        call_args = mock_layout.info_label.set_text.call_args[0][0]
        assert "Name:" in call_args
        assert "Health:</b> 80" in call_args
        assert "Happiness:</b> 70" in call_args

    def test_update_selection_window_multiple(self, renderer, mock_layout, mock_world, mock_gm):
        """Test updating selection window for multiple entities."""
        e1 = 1
        e2 = 2

        # Mock components for e1 (Yukkuri)
        stats1 = YukkuriStats(name="Marisa", type_id="marisa", health=100.0)
        emotional1 = EmotionalState(happiness=100.0)

        # Mock components for e2 (Item)
        item_stats = ItemStats(name="Cookie", type_id="cookie", cost=10)

        def get_component(eid, comp_type):
            if eid == e1:
                if comp_type == YukkuriStats: return stats1
                if comp_type == EmotionalState: return emotional1
                if comp_type == ItemStats: return None
            elif eid == e2:
                if comp_type == YukkuriStats: return None
                if comp_type == ItemStats: return item_stats
            return None

        mock_world.get_component.side_effect = get_component

        renderer.update(0.016, [e1, e2], False)

        assert mock_layout.info_label.set_text.called
        call_args = mock_layout.info_label.set_text.call_args[0][0]
        assert "Selected: 2 entities" in call_args
        assert "Yukkuris: 1" in call_args
        assert "Items: 1" in call_args

    def test_update_debug_window(self, renderer, mock_layout, mock_world):
        """Test updating debug window."""
        mock_world.get_all_entities.return_value = [1, 2, 3]
        renderer.fps = 60.0

        renderer.update(0.016, [], True)

        assert mock_layout.debug_text_box.set_text.called
        call_args = mock_layout.debug_text_box.set_text.call_args[0][0]
        assert "FPS:</b> 60.00" in call_args
        assert "Entities:</b> 3" in call_args

    def test_draw_selection_box(self, renderer, mock_world, monkeypatch):
        """Test drawing selection box when dragging."""
        input_service = MagicMock(spec=InputService)
        input_service.is_dragging = True
        input_service.drag_start_pos = (10, 10)
        input_service.drag_current_pos = (50, 50)

        mock_world.services.try_get.return_value = input_service

        screen = MagicMock(spec=pygame.Surface)

        # Patch pygame.draw.rect
        mock_draw_rect = MagicMock()
        monkeypatch.setattr(pygame.draw, "rect", mock_draw_rect)

        renderer.draw(screen)

        mock_draw_rect.assert_called()
        args = mock_draw_rect.call_args[0]
        assert args[0] == screen
        assert args[1] == (0, 255, 0) # Green color
        assert args[2] == pygame.Rect(10, 10, 40, 40)
        assert args[3] == 1 # Width

    def test_update_hover_tooltip(self, renderer, mock_world, mock_layout):
        """Test updating hover tooltip."""
        input_service = MagicMock(spec=InputService)
        input_service.hovered_entity_id = 1
        input_service.hovered_entity_pos = (100, 100)
        mock_world.services.try_get.return_value = input_service

        # Entity exists and has stats
        mock_world.entity_exists.return_value = True
        stats = YukkuriStats(name="TestYukkuri", type_id="test", health=50)
        mock_world.get_component.return_value = stats

        renderer._update_hover_tooltip()

        mock_layout.update_hover_tooltip.assert_called_with(
            "<b>TestYukkuri</b><br>HP: 50",
            (100, 100)
        )

    def test_draw_relationship_lines(self, renderer, mock_world, monkeypatch):
        """Test drawing relationship lines."""
        selected_id = 1
        other_id = 2

        # Mock components
        my_trans = Transform(x=100, y=100)
        other_trans = Transform(x=200, y=200)

        registry = RelationshipRegistry()
        from yukkuri_game.game.yukkuri_components import RelationshipData
        rel_data = RelationshipData(affinity=50)
        registry.relationships[other_id] = rel_data

        def get_component(eid, comp_type):
            if eid == selected_id:
                if comp_type == Transform: return my_trans
                if comp_type == RelationshipRegistry: return registry
            elif eid == other_id:
                if comp_type == Transform: return other_trans
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.entity_exists.return_value = True

        # Mock pygame display surface
        mock_screen = MagicMock(spec=pygame.Surface)

        monkeypatch.setattr(pygame.display, "get_surface", lambda: mock_screen)
        mock_draw_line = MagicMock()
        monkeypatch.setattr(pygame.draw, "line", mock_draw_line)

        renderer._draw_relationship_lines(selected_id)

        mock_draw_line.assert_called()
        args = mock_draw_line.call_args[0]
        # Verify line drawn between transforms with correct color (green-ish for positive affinity)
        assert args[0] == mock_screen
        assert args[2] == (100, 100)
        assert args[3] == (200, 200)
        # Check color component (green dominant)
        assert args[1][1] > args[1][0] and args[1][1] > args[1][2]
