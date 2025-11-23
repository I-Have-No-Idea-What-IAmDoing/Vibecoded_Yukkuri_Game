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
from .game.yukkurrium import Yukkurrium, RenderSystem, TimeSystem
from .game.game_manager import GameManager
from .game.services import EconomyService, PersistenceService, TimeService, InputService
from .game.settings_service import SettingsService
from .game.entity_factory import EntityFactory
from .game.ai.utility import UtilityAIEngine
from .game.systems.stat_decay import StatDecaySystem
from .game.systems.lifecycle import LifecycleSystem
from .game.systems.decision import DecisionSystem
from .game.systems.behavior import BehaviorSystem
from .game.systems.physics import PhysicsSystem
from .game.systems.construction_system import ConstructionSystem
from .game.systems.animation import AnimationSystem
from .game.systems.poop_system import PoopSystem
from .game.systems.feedback_system import FeedbackSystem
from .game.systems.interaction_system import InteractionSystem
from .game.systems.social_system import SocialSystem
from .game.ui.hud import HUD
from .game.input_system import InputSystem
from .game.yukkuri_components import AIState # Fix import for HUD string check if needed
from .config import load_config

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

    def setup(self) -> None:
        """
        Sets up the game environment, systems, and initial state.

        Initializes ECS systems, UI, and initial entities.

        Returns:
            None
        """
        # Load Config
        self.game_config = load_config()

        # Core Systems & Service Registration
        self.yukkurrium = Yukkurrium(settings=self.game_config.world)
        self.audio = AudioManager()

        # Load sounds
        if os.path.exists("data/sounds.toml"):
            try:
                import tomllib # python 3.11
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    tomllib = None

            if tomllib:
                with open("data/sounds.toml", "rb") as f:
                    sounds = tomllib.load(f)
                    for name, path in sounds.get("sounds", {}).items():
                        self.audio.load_sound(name, path)
            else:
                # Fallback if no toml parser
                self.audio.load_sound("click", "data/audio/click.wav")
                self.audio.load_sound("place", "data/audio/place.wav")
                self.audio.load_sound("cancel", "data/audio/cancel.wav")
                self.audio.load_sound("sell", "data/audio/sell.wav")
                self.audio.load_sound("train", "data/audio/train.wav")
                self.audio.load_sound("eat", "data/audio/eat.wav")
                self.audio.load_sound("cry", "data/audio/cry.wav")
        else:
             # Hardcoded fallback
            self.audio.load_sound("click", "data/audio/click.wav")
            self.audio.load_sound("place", "data/audio/place.wav")
            self.audio.load_sound("cancel", "data/audio/cancel.wav")
            self.audio.load_sound("sell", "data/audio/sell.wav")
            self.audio.load_sound("train", "data/audio/train.wav")
            self.audio.load_sound("eat", "data/audio/eat.wav")
            self.audio.load_sound("cry", "data/audio/cry.wav")

        self.physics_system = PhysicsSystem()
        self.event_bus = EventBus()

        self.world.services.register(self.resources, ResourceManager)
        self.world.services.register(self.audio, AudioManager)
        self.world.services.register(self.yukkurrium)
        self.world.services.register(self.physics_system)
        self.world.services.register(self.event_bus)

        # Services
        self.economy_service = EconomyService()
        self.world.services.register(self.economy_service)

        self.time_service = TimeService()
        self.world.services.register(self.time_service)

        self.input_service = InputService()
        self.world.services.register(self.input_service)

        self.persistence_service = PersistenceService(self.world)
        self.world.services.register(self.persistence_service)

        self.settings_service = SettingsService()
        self.world.services.register(self.settings_service)

        # Apply initial settings
        audio_settings = self.settings_service.settings.get("audio", {})
        self.audio.set_master_volume(audio_settings.get("master_volume", 0.5))
        self.audio.set_bgm_volume(audio_settings.get("bgm_volume", 0.5))
        self.audio.set_sfx_volume(audio_settings.get("sfx_volume", 0.5))

        window_settings = self.settings_service.settings.get("window", {})
        width = window_settings.get("width", 1280)
        height = window_settings.get("height", 720)
        fullscreen = window_settings.get("fullscreen", False)

        # Apply window settings if different from default
        if not self.headless:
             flags = pygame.RESIZABLE
             if fullscreen:
                 flags |= pygame.FULLSCREEN
             try:
                 # Update screen and ui_manager if resolution changed
                 if width != self.width or height != self.height or fullscreen:
                      self.screen = pygame.display.set_mode((width, height), flags)
                      self.width = width
                      self.height = height
                      self.ui_manager.set_window_resolution((width, height))
                      # Also update hud layout dimensions if needed, but hud is created after this
             except pygame.error as e:
                 print(f"Failed to set initial video mode: {e}")

        # Factory & Game Manager
        self.factory = EntityFactory(self.world)
        self.world.services.register(self.factory)

        self.gm = GameManager(self.world)
        self.world.services.register(self.gm)

        # AI
        self.ai_engine = UtilityAIEngine(self.resources)
        self.ai_engine.validate_actions()
        # Could register AI engine if needed by others, e.g. YukkuriAISystem might fetch it?
        # For now YukkuriAISystem takes it in constructor, but let's register it just in case.
        self.world.services.register(self.ai_engine)

        # Add Systems
        self.input_system = InputSystem(self.yukkurrium)
        self.world.add_system(self.input_system) # Update doesn't do much, events handled separately

        self.world.add_system(TimeSystem())
        self.world.add_system(self.physics_system)
        self.world.add_system(StatDecaySystem(settings=self.game_config.rules.stat_decay))
        self.world.add_system(LifecycleSystem(settings=self.game_config.rules.lifecycle, entity_factory=self.factory))
        self.world.add_system(DecisionSystem(self.ai_engine, decision_interval=1.0))
        self.world.add_system(BehaviorSystem(float(self.yukkurrium.width), float(self.yukkurrium.height)))
        self.world.add_system(ConstructionSystem())
        self.world.add_system(AnimationSystem())
        self.world.add_system(PoopSystem())
        self.world.add_system(FeedbackSystem(self.world))
        self.world.add_system(InteractionSystem())
        self.world.add_system(SocialSystem(self.world))

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
        if not self.headless:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.hud.toggle_debug()
                elif event.key == pygame.K_F12:
                    self.take_screenshot()

            self.input_system.handle_event(event, self.world, self.width, self.height, self.ui_manager)
            self.hud.process_event(event)

    def update(self) -> None:
        """
        Updates the game state each frame.

        Advances time in the GameManager and updates the Yukkurrium (camera).

        Returns:
            None
        """
        if not self.paused:
            self.gm.time_elapsed += self.dt * self.time_scale

        super().update()
        self.yukkurrium.update(self.dt)

        if not self.headless:
            self.hud.fps = self.clock.get_fps()
            self.hud.update(self.dt)

    def render_world(self) -> None:
        """
        Renders the game world using the RenderSystem.

        Returns:
            None
        """
        if not self.headless and self.render_system:
            self.render_system.update(self.world, self.dt)

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
        self.screen = pygame.display.get_surface()

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
        print(f"Screenshot saved to {filename}")

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

    game = YukkuriGame()
    if args.headless:
        game.set_headless(True)

    game.run()

if __name__ == "__main__":
    main()
