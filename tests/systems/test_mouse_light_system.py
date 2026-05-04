import pytest
from unittest.mock import Mock, patch
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.mouse_light_system import MouseLightSystem
from yukkuri_game.game.components import Transform, LightSource
from yukkuri_game.game.services import InputService
from yukkuri_game.engine.input_manager import InputManager
from yukkuri_game.game.camera import Camera


class TestMouseLightSystem:
    @pytest.fixture
    def mock_camera(self):
        camera = Mock(spec=Camera)
        camera.screen_to_world.side_effect = lambda mx, my, sw, sh: (mx + 10, my + 10)
        return camera

    @pytest.fixture
    def world(self):
        w = World()
        w.services.register(Mock(spec=InputService), InputService)
        w.services.register(Mock(spec=InputManager), InputManager)
        return w

    @pytest.fixture
    def system(self, world, mock_camera):
        from yukkuri_game.game.camera import Camera
        world.services.register(mock_camera, Camera)
        with patch(
            "yukkuri_game.game.systems.mouse_light_system.pygame"
        ) as mock_pygame:
            mock_pygame.display.get_surface.return_value.get_size.return_value = (
                800,
                600,
            )
            sys = MouseLightSystem()
            world.add_system(sys)
            yield sys

    def test_initialization(self, system, world):
        assert system.enabled is False
        assert system.light_entity is not None

        # Verify components
        assert world.has_component(system.light_entity, Transform)
        assert world.has_component(system.light_entity, LightSource)

        light = world.get_component(system.light_entity, LightSource)
        assert light.intensity == 0.0

    def test_toggle(self, system, world):
        system.toggle()
        assert system.enabled is True
        light = world.get_component(system.light_entity, LightSource)
        assert light.intensity == 0.8

        system.toggle()
        assert system.enabled is False
        light = world.get_component(system.light_entity, LightSource)
        assert light.intensity == 0.0

    def test_update_disabled(self, system, world, mock_camera):
        system.enabled = False

        # Mock input
        input_manager = world.services.get(InputManager)
        input_manager.get_mouse_position.return_value = (100, 100)

        system.update(world, 0.1)

        # Camera shouldn't be called
        mock_camera.screen_to_world.assert_not_called()

    def test_update_enabled(self, system, world, mock_camera):
        system.enabled = True

        # Mock input
        input_manager = world.services.get(InputManager)
        input_manager.get_mouse_position.return_value = (100, 100)

        with patch(
            "yukkuri_game.game.systems.mouse_light_system.pygame"
        ) as mock_pygame:
            mock_pygame.display.get_surface.return_value.get_size.return_value = (
                800,
                600,
            )

            system.update(world, 0.1)

            mock_camera.screen_to_world.assert_called_with(100, 100, 800, 600)

            transform = world.get_component(system.light_entity, Transform)
            # Our mock camera adds 10 to coords
            assert transform.x == 110
            assert transform.y == 110
