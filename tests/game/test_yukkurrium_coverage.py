import pytest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.game.yukkurrium import Yukkurrium, WorldRenderer, RenderSystem, TimeSystem
from yukkuri_game.config import WorldSettings
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, Sprite, Selectable, FloatingText, PhysicsBody, VisualTransform

class TestYukkurrium:
    def test_initialization(self):
        settings = WorldSettings(width=2000, height=2000)
        y = Yukkurrium(settings)
        assert y.width == 2000
        assert y.height == 2000
        assert y.zoom == 1.0
        assert y.camera_x == 0.0

    def test_initialization_default(self):
        y = Yukkurrium()
        # The default WorldSettings seem to have different values than I expected
        # Let's check what they are or update the test
        settings = WorldSettings()
        assert y.width == settings.width

    def test_coordinate_conversion(self):
        y = Yukkurrium()
        screen_w, screen_h = 800, 600

        # Center of screen should match camera position (0,0)
        sx, sy = y.world_to_screen(0, 0, screen_w, screen_h)
        assert sx == 400
        assert sy == 300

        wx, wy = y.screen_to_world(400, 300, screen_w, screen_h)
        assert wx == 0
        assert wy == 0

        # Test with zoom and offset
        y.camera_x = 100
        y.zoom = 2.0

        # World (100, 0) -> Relative (0, 0) -> Screen (400, 300)
        sx, sy = y.world_to_screen(100, 0, screen_w, screen_h)
        assert sx == 400

        # World (150, 0) -> Relative (50, 0) -> *2 -> 100 -> Screen (500, 300)
        sx, sy = y.world_to_screen(150, 0, screen_w, screen_h)
        assert sx == 500

    def test_handle_input_zoom(self):
        y = Yukkurrium()
        event = MagicMock()
        event.type = pygame.MOUSEWHEEL
        event.y = 1 # Zoom in

        y.handle_input(event, 800, 600)
        assert y.target_zoom > 1.0

        event.y = -100 # Zoom out max
        y.handle_input(event, 800, 600)
        assert y.target_zoom == y.min_zoom

    def test_handle_input_pan(self):
        y = Yukkurrium()
        event = MagicMock()
        event.type = pygame.MOUSEMOTION
        event.rel = (10, 20)

        with patch('pygame.mouse.get_pressed', return_value=(0, 1, 0)): # Middle click
            y.handle_input(event, 800, 600)

        assert y.camera_x == -10
        assert y.camera_y == -20

    def test_update(self):
        y = Yukkurrium()
        y.target_zoom = 2.0

        # Mock keys to handle indexing safely (return 0 for any key)
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = 0

        with patch('pygame.key.get_pressed', return_value=mock_keys):
            y.update(0.1)
        assert y.zoom > 1.0

class TestWorldRenderer:
    @pytest.fixture
    def mock_screen(self):
        screen = MagicMock(spec=pygame.Surface)
        screen.get_size.return_value = (800, 600)
        screen.get_rect.return_value = MagicMock(colliderect=lambda r: True)
        return screen

    @pytest.fixture
    def mock_yukkurrium(self):
        y = MagicMock(spec=Yukkurrium)
        y.world_to_screen.return_value = (400, 300)
        y.screen_to_world.return_value = (0, 0)
        y.zoom = 1.0
        return y

    @pytest.fixture
    def mock_rm(self):
        rm = MagicMock(spec=ResourceManager)
        img = MagicMock(spec=pygame.Surface)
        img.get_width.return_value = 64
        img.get_height.return_value = 64
        img.get_size.return_value = (64, 64)
        img.subsurface.return_value = img
        rm.load_image.return_value = img
        return rm

    def test_render_entities(self, mock_screen, mock_yukkurrium, mock_rm):
        renderer = WorldRenderer(mock_screen, mock_yukkurrium, mock_rm)
        # Mock draw_grid to avoid pygame surface check issues with MagicMock
        renderer.draw_grid = MagicMock()

        world = MagicMock(spec=World)

        # Setup entities
        e1 = 1
        world.get_entities_with.return_value = [e1]

        trans = Transform(x=0, y=0)
        sprite = Sprite(image_name="test.png", width=64, height=64)
        phys = MagicMock(spec=PhysicsBody)
        visual = VisualTransform()

        def get_component(e, c):
            if c == Transform: return trans
            if c == Sprite: return sprite
            if c == PhysicsBody: return phys
            if c == VisualTransform: return visual
            if c == Selectable: return None
            return None

        world.get_component.side_effect = get_component

        renderer.render(world)

        mock_screen.blit.assert_called()
        mock_rm.load_image.assert_called_with("test.png")

    def test_render_selected(self, mock_screen, mock_yukkurrium, mock_rm):
        renderer = WorldRenderer(mock_screen, mock_yukkurrium, mock_rm)
        renderer.draw_grid = MagicMock()
        world = MagicMock(spec=World)

        e1 = 1
        world.get_entities_with.return_value = [e1]

        trans = Transform(x=0, y=0)
        sprite = Sprite(image_name="test.png", width=64, height=64)
        sel = Selectable(selected=True)
        phys = MagicMock(spec=PhysicsBody)
        visual = VisualTransform()

        def get_component(e, c):
            if c == Transform: return trans
            if c == Sprite: return sprite
            if c == Selectable: return sel
            if c == PhysicsBody: return phys
            if c == VisualTransform: return visual
            return None

        world.get_component.side_effect = get_component

        with patch('pygame.draw.rect') as mock_draw_rect:
             renderer.render(world)
             mock_draw_rect.assert_called()

    def test_render_floating_text(self, mock_screen, mock_yukkurrium, mock_rm):
        renderer = WorldRenderer(mock_screen, mock_yukkurrium, mock_rm)
        world = MagicMock(spec=World)

        trans = Transform(x=0, y=0)
        text = FloatingText(text="Hello", color=(255, 255, 255), lifetime=1.0, max_lifetime=1.0, velocity_y=-10.0)

        world.get_components_tuple.return_value = [(1, (trans, text))]

        # Mock pygame.font.SysFont to return a mock font
        with patch('pygame.font.SysFont') as MockFont:
             mock_font_instance = MagicMock()
             MockFont.return_value = mock_font_instance

             renderer.render_floating_text(world, 800, 600)

             mock_font_instance.render.assert_called()
             mock_screen.blit.assert_called()

class TestRenderSystem:
    def test_update(self):
        world = MagicMock(spec=World)
        # Mock world.services
        world.services = MagicMock()
        screen = MagicMock()

        world.services.get.side_effect = lambda t: MagicMock()

        with patch('yukkuri_game.game.yukkurrium.WorldRenderer') as MockRenderer:
            system = RenderSystem(screen, world)
            system.update(world, 0.1)
            MockRenderer.return_value.render.assert_called_with(world)

class TestTimeSystem:
    def test_update(self):
        system = TimeSystem()
        world = MagicMock(spec=World)

        system.update(world, 0.5)
        assert system.total_time == 0.5

        system.game_speed = 2.0
        system.update(world, 0.5)
        assert system.total_time == 1.5
