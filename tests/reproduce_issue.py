
import os
import pygame
import pygame_gui
import pygame_light2d as pl2d
from unittest.mock import MagicMock, patch
import pytest
from yukkuri_game.scenes.main_menu import MainMenuScene
from yukkuri_game.engine.scene import Scene
from yukkuri_game.engine.input_manager import InputManager

class TestMainMenuRender:
    def test_render_with_lights_engine(self):
        """
        Verify that MainMenuScene renders to lights_engine if it exists.
        """
        pygame.init()
        # Create a 1x1 window to satisfy pygame.display.get_surface requirements if needed
        pygame.display.set_mode((1, 1))

        # Mock Application
        app = MagicMock()
        app.width = 800
        app.height = 600
        app.headless = False
        app.screen = MagicMock()

        # Mock LightingEngine
        lights_engine = MagicMock()
        app.lights_engine = lights_engine

        # Mock SceneManager
        app.scene_manager = MagicMock()

        # Mock Services
        app.resources = MagicMock()
        app.input_manager = MagicMock()
        app.event_manager = MagicMock()

        # Mock InputManager registration
        # Since we mock app.input_manager, we rely on Scene.__init__ to register it?
        # But Scene uses esper.World which we are not mocking directly, so it uses real World.
        # But we mock the services inside it indirectly by mocking app components passed to it.

        # Wait, if we use real Scene, it creates real World.
        # services.register(app.input_manager, InputManager) will register the mock.
        # So services.get(InputManager) will return the mock. Correct.

        scene = MainMenuScene(app)

        # Mock ui_manager to avoid actual drawing logic that might fail without resources or display
        scene.ui_manager = MagicMock()

        # Call render
        scene.render()

        # Assertions

        if lights_engine.surface_to_texture.called:
                print("PASS: Called surface_to_texture")
        else:
                pytest.fail("FAIL: Did not call surface_to_texture")

        if lights_engine.render_texture.called:
                print("PASS: Called render_texture")
        else:
                pytest.fail("FAIL: Did not call render_texture")

if __name__ == "__main__":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    t = TestMainMenuRender()
    try:
        t.test_render_with_lights_engine()
        print("Test passed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Test failed: {e}")
