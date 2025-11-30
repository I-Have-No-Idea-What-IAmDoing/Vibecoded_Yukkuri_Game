"""
Main entry point for the Yukkuri Raising Game.
"""
import sys
import os
from datetime import datetime
import argparse
import pygame
from .engine.core import GameLoop
from .engine.audio import AudioManager
from .engine.resource_manager import ResourceManager
from .engine.event_bus import EventBus
from .game.events import GamePausedEvent, TogglePauseRequest, CycleSpeedRequest, ResolutionChangedEvent
from .game.yukkurrium import Yukkurrium, RenderSystem
from .game.game_manager import GameManager
from .game.services import EconomyService, PersistenceService, TimeService, InputService, GameService
from .game.settings_service import SettingsService
from .game.trait_service import TraitService
from .game.entity_factory import EntityFactory
from .game.ai.utility import UtilityAIEngine
from .game.systems.physics import PhysicsSystem
from .game.ui.hud import HUD
from .config import load_config
from .system_registry import SystemRegistry
from loguru import logger

class YukkuriGame(GameLoop):
    """
    The main game class inheriting from GameLoop.

    Orchestrates the setup, update, and rendering of the Yukkuri Raising Game.

    Attributes:
        yukkurrium (Yukkurrium): The game world view and camera manager.
        audio (AudioManager): The audio manager.
        factory (EntityFactory): The factory for creating entities.
        gm (GameManager): The game manager for high-level logic.
        ai_engine (UtilityAIEngine): The AI engine.
        input_system (InputSystem): The system handling input events.
        render_system (RenderSystem): The system responsible for rendering (when not headless).
        hud (HUD): The Heads-Up Display (when not headless).
    """
    def __init__(self, headless: bool = False):
        """
        Initializes the YukkuriGame.

        Args:
            headless (bool): Whether to run in headless mode. Defaults to False.
        """
        super().__init__(headless=headless)

    def setup(self) -> None:
        """
        Sets up the game environment, systems, and initial state.

        Initializes ECS systems, UI, and initial entities.

        Returns:
            None
        """
        if self.is_setup:
            return
        self.is_setup = True

        # Load Config
        self.game_config = load_config()

        # Core Systems & Service Registration
        self.yukkurrium = Yukkurrium(settings=self.game_config.world)
        self.audio = AudioManager()
        self.audio.load_from_config()

        self.physics_system = PhysicsSystem()
        self.event_bus = EventBus()

        self._register_core_services()
        self._register_game_services()
        self._apply_initial_settings()
        self._register_factories_and_managers()
        self._register_systems()

    def _register_core_services(self) -> None:
        """Registers core services to the ServiceLocator."""
        self.world.services.register(self.resources, ResourceManager)
        self.world.services.register(self.audio, AudioManager)
        self.world.services.register(self.yukkurrium, Yukkurrium)
        self.world.services.register(self.physics_system, PhysicsSystem)
        self.world.services.register(self.event_bus, EventBus)

    def _register_game_services(self) -> None:
        """Registers game-specific services."""
        self.economy_service = EconomyService()
        self.world.services.register(self.economy_service, EconomyService)

        self.time_service = TimeService()
        self.world.services.register(self.time_service, TimeService)

        self.input_service = InputService()
        self.world.services.register(self.input_service, InputService)

        self.persistence_service = PersistenceService(self.world)
        self.world.services.register(self.persistence_service, PersistenceService)

        self.settings_service = SettingsService()
        self.world.services.register(self.settings_service, SettingsService)

        self.trait_service = TraitService(self.world)
        self.world.services.register(self.trait_service, TraitService)

    def _apply_initial_settings(self) -> None:
        """Applies initial audio and video settings."""
        audio_settings = self.settings_service.settings.get("audio", {})
        self.audio.set_master_volume(audio_settings.get("master_volume", 0.5))
        self.audio.set_bgm_volume(audio_settings.get("bgm_volume", 0.5))
        self.audio.set_sfx_volume(audio_settings.get("sfx_volume", 0.5))

        window_settings = self.settings_service.settings.get("window", {})
        width = window_settings.get("width", 1280)
        height = window_settings.get("height", 720)
        fullscreen = window_settings.get("fullscreen", False)

        if not self.headless:
             flags = pygame.RESIZABLE
             if fullscreen:
                 flags |= pygame.FULLSCREEN
             try:
                 if width != self.width or height != self.height or fullscreen:
                      self.screen = pygame.display.set_mode((width, height), flags)
                      self.width = width
                      self.height = height
                      self.ui_manager.set_window_resolution((width, height))
             except pygame.error as e:
                 logger.error(f"Failed to set initial video mode: {e}")

    def _register_factories_and_managers(self) -> None:
        """Registers factories and high-level managers."""
        self.factory = EntityFactory(self.world)
        self.world.services.register(self.factory, EntityFactory)

        self.gm = GameManager(self.world)
        self.world.services.register(self.gm, GameManager)

        self.game_service = GameService(self.world)
        self.world.services.register(self.game_service, GameService)

        self.ai_engine = UtilityAIEngine(self.resources)
        self.ai_engine.validate_actions()
        self.world.services.register(self.ai_engine, UtilityAIEngine)

    def _register_systems(self) -> None:
        """Registers and adds all ECS systems."""
        self.input_system = SystemRegistry.register_systems(
            self.world,
            self.game_config,
            self.yukkurrium,
            self.factory,
            self.event_bus,
            self.physics_system
        )

        if not self.headless:
            self.render_system = RenderSystem(self.screen, self.world)
            # RenderSystem is not added to world updates because it should be called in render_world
            # self.world.add_system(self.render_system)

            # UI
            self.hud = HUD(self.ui_manager, self.world)

            # Subscribe to events for game control
            self.event_bus.subscribe(TogglePauseRequest, lambda e: self.toggle_pause())
            self.event_bus.subscribe(CycleSpeedRequest, lambda e: self.cycle_speed())
            self.event_bus.subscribe(ResolutionChangedEvent, self.on_resolution_changed)

        # Initial Population
        if not self.headless:
            # Create a starting Reimu
            start_x = float(self.yukkurrium.width) / 2.0
            start_y = float(self.yukkurrium.height) / 2.0
            self.factory.create_yukkuri("reimu", start_x, start_y)

            # Center camera on start
            self.yukkurrium.camera_x = float(start_x)
            self.yukkurrium.camera_y = float(start_y)

    def on_event(self, event: pygame.event.Event) -> None:
        """
        Handles input events specific to the game.

        Args:
            event: The Pygame event.

        Returns:
            None
        """
        # Always handle input system events to support testing injection
        if hasattr(self, 'input_system') and self.input_system:
            self.input_system.handle_event(event, self.world, self.width, self.height, self.ui_manager)

        if not self.headless:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.hud.toggle_debug()
                elif event.key == pygame.K_F12:
                    self.take_screenshot()

            self.hud.process_event(event)

    def tick(self, dt: float) -> None:
        """
        Updates the game state each frame with a given delta time.

        Args:
            dt (float): The delta time in seconds.

        Returns:
            None
        """
        if not self.paused:
            self.gm.time_elapsed += dt * self.time_scale
            # Also update TimeService
            if hasattr(self, 'time_service'):
                self.time_service.time_elapsed = self.gm.time_elapsed

        super().tick(dt)
        self.yukkurrium.update(dt)

        if not self.headless:
            self.hud.fps = self.clock.get_fps()
            self.hud.update(dt)

    def render(self) -> None:
        """
        Render the game world.
        """
        self.screen.fill((30, 30, 30)) # Dark background

        self.render_world()

        # Draw HUD overlays (like selection box)
        if not self.headless and self.hud:
            self.hud.draw(self.screen)

        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def render_world(self) -> None:
        """
        Renders the game world using the RenderSystem.

        Returns:
            None
        """
        # In headless mode, we might still want to render for screenshots if requested.
        # But we need to ensure render_system is initialized or we do it ad-hoc.
        # The current GameDriver calls this manually.

        if self.headless and not hasattr(self, 'render_system'):
             # If strictly headless but we want to render, we might need to init render system temporarily
             # or we just rely on the fact that if set_headless(True) is called, render_system isn't created.
             # But for screenshots, we might want it.
             self.render_system = RenderSystem(self.screen, self.world)

        if hasattr(self, 'render_system') and self.render_system:
            self.render_system.update(self.world, self.dt)

    def init_render_system_headless(self) -> None:
        """
        Manually initializes the render system in headless mode if it doesn't exist.
        Useful for screenshot capabilities in tests.
        """
        if self.headless and not hasattr(self, 'render_system'):
            self.render_system = RenderSystem(self.screen, self.world)

    def toggle_pause(self) -> None:
        """
        Toggles the paused state of the simulation.

        Returns:
            None
        """
        self.paused = not self.paused
        self.event_bus.publish(GamePausedEvent(self.paused))

    def cycle_speed(self) -> None:
        """
        Cycles through available game simulation speeds (1.0, 2.0, 5.0, 0.5).

        Returns:
            None
        """
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0

        self.time_scale = speeds[next_idx]
        if self.hud.layout.speed_btn:
            self.hud.layout.speed_btn.set_text(f"{self.time_scale}x")

    def on_resolution_changed(self, event: ResolutionChangedEvent) -> None:
        """
        Handles resolution change events.

        Args:
            event (ResolutionChangedEvent): The resolution changed event.
        """
        if self.headless:
            return

        self.width = event.width
        self.height = event.height

        # Note: pygame.display.set_mode is handled in HudEvents initially,
        # but ideally should be handled centrally.
        # However, since screen surface is returned by set_mode, we might need to update self.screen here
        # if HudEvents called it.
        # Actually, calling set_mode again returns the same surface if compatible or new one.
        surface = pygame.display.get_surface()
        if surface:
            self.screen = surface

        # Notify HUD
        if self.hud:
            self.hud.resize(self.width, self.height)

    def take_screenshot(self) -> None:
        """
        Captures a screenshot and saves it to the 'screenshots' directory.

        Returns:
            None
        """
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pygame.image.save(self.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

def main() -> None:
    """
    The entry point for the application.

    Parses command-line arguments and starts the game loop.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Yukkuri Raising Game")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no window)")
    args = parser.parse_args()

    game = YukkuriGame(headless=args.headless)
    game.run()

if __name__ == "__main__":
    main()
