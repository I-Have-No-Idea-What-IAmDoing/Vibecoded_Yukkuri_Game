"""
GameDriver module for integration testing.
"""

from src.yukkuri_game.engine.application import Application
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.services import GameService
# Fix import path
from yukkuri_game.scenes.gameplay import GameplayScene
import pygame
import os

class GameDriver:
    """
    Control class for driving the game application in tests.
    """

    def __init__(self, app: Application):
        self.app = app
        self.world: World = None  # Will be set during setup
        self.simulated_time = 0.0
        self.frame_count = 0

    # Helper properties for existing tests
    @property
    def game(self):
        return self.app

    def setup(self):
        """Initializes the game and enters the main scene."""
        # Force headless if not set (though Application likely handles it)
        if not self.app.headless:
             # In integration tests, we might want headless
             pass

        # We need to manually trigger scene loading because run() loop isn't used
        # Create GameplayScene (registered as "gameplay" or similar in scene manager)
        # Note: SceneManager in this project seems to use push/replace, not switch_scene by name
        # We need to instantiate the scene manually
        try:
            scene = GameplayScene(self.app)
            self.app.scene_manager.push(scene)

            # Advance one frame to ensure initialization
            self.app.update(0.016)

            scene = self.app.scene_manager.current_scene
            if isinstance(scene, GameplayScene):
                self.world = scene.world
            else:
                 # If scene failed to push or was replaced, we might be in trouble, but let's try to get world
                 if scene:
                     self.world = getattr(scene, 'world', None)
        except Exception as e:
            print(f"Warning: GameDriver setup encountered error: {e}")
            # Do not crash setup if possible, let test fail if world is None

    def run_for(self, duration: float, step: float = 1/60) -> None:
        """
        Advances the game simulation for a specified duration.
        """
        elapsed = 0.0
        while elapsed < duration:
            self.app.update(step)
            elapsed += step
            self.simulated_time += step
            self.frame_count += 1

    def save_screenshot(self, filename: str) -> None:
        """
        Saves the current frame to an image file.
        Also initializes headless render system if needed.
        """
        self.app.init_render_system_headless()

        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if self.app.lights_engine:
            # OpenGL mode
            # We need to read pixels from the framebuffer
            # Assuming lights_engine.ctx is the moderngl context
             try:
                # Capture from default framebuffer (screen)
                # Note: This might capture back buffer or front buffer depending on state.
                # Since we didn't call flip/swap, and just rendered, it should be in back buffer.
                # read() usually reads from currently bound read framebuffer.

                # Check if ctx and screen are valid
                if self.app.lights_engine.ctx and self.app.lights_engine.ctx.screen:
                    size = self.app.lights_engine.ctx.screen.size
                    # print(f"OpenGL Screen Size: {size}")

                    buffer = self.app.lights_engine.ctx.screen.read(components=3)
                    image = pygame.image.fromstring(buffer, size, "RGB")
                    # OpenGL images are upside down usually
                    image = pygame.transform.flip(image, False, True)
                    pygame.image.save(image, filename)
                    # print(f"Saved screenshot to {filename}")
                    return
             except Exception as e:
                 print(f"Failed to capture OpenGL screenshot: {e}")

        # Fallback to surface save
        pygame.image.save(self.app.screen, filename)

    def cleanup(self):
        self.app.quit()
