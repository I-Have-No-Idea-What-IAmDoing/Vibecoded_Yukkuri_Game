"""
Gameplay Scene.

This module defines the `GameplayScene`, which is the primary interactive scene
where the game simulation occurs. It manages the lifecycle of game systems, UI,
and world state.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
import pygame_gui
from loguru import logger

if TYPE_CHECKING:
    from ..game.systems.day_night import DayNightSystem

from ..config import load_config
from ..engine.application import Application
from ..engine.audio import AudioManager
from ..engine.event_manager import EventManager, GamePhase
from ..engine.input_manager import InputContext, InputManager
from ..engine.scene import Scene, SceneContext
from ..engine.serializer import WorldSerializer
from ..game import components, yukkuri_components
from ..game.ai.navigation_service import NavigationService
from ..game.camera import Camera
from ..game.events import (
    CycleSpeedRequest,
    GamePausedEvent,
    LoadGameRequest,
    ResolutionChangedEvent,
    SaveGameRequest,
    TogglePauseRequest,
)
from ..game.loader import GameLoader
from ..game.prefabs.yukkuri import create_yukkuri
from ..game.services import EconomyService, GameService, TimeService
from ..game.settings_service import SettingsService
from ..game.systems.mouse_light_system import MouseLightSystem
from ..game.systems.physics import PhysicsSystem
from ..game.systems.physics_reconstruction import reconstruct_physics
from ..game.systems.render_system import RenderSystem
from ..game.ui.hud import HUD


class GameplayScene(Scene):
    """
    The main gameplay scene.

    Manages the game world, systems, and UI.

    Attributes:
        is_setup (bool): Whether the scene has been initialized.
        paused (bool): Whether the game simulation is paused.
        time_scale (float): The current speed multiplier for game time.
        ui_manager (pygame_gui.UIManager): The UI manager for this scene.
        dt (float): The delta time for the current frame.
        render_system (RenderSystem | None): The rendering system.
        day_night_system (DayNightSystem | None): The day/night cycle system.
        hud (HUD | None): The Heads-Up Display manager.
        game_config (Any): The loaded game configuration.
        camera (Camera): The game camera.
        audio (AudioManager): The audio manager.
        physics_system (PhysicsSystem): The physics system.
        event_manager (EventManager): The event manager.
        event_bus (Any): The event bus.
        input_manager (InputManager): The input manager.
        loader (GameLoader): The game loader.
        economy_service (EconomyService): The economy service.
        time_service (TimeService): The time service.
        settings_service (SettingsService): The settings service.
        game_service (GameService): The game service.
        serializer (WorldSerializer): The world serializer.
        input_system (Any): The input system.
    """

    INJECTIONS: ClassVar[dict[str, type]] = {"money": int, "time": float}

    def __init__(self, application: Application) -> None:
        """
        Initializes the GameplayScene.

        Args:
            application (Application): The main application instance.
        """
        super().__init__(application)
        self.is_setup = False
        self.paused = False
        self.time_scale = 1.0
        # Compute absolute path for theme file (relative to project root)
        _theme_path = (
            Path(__file__).parent.parent.parent.parent / "data" / "ui_theme.json"
        )
        logger.debug(
            f"Gameplay theme path: {_theme_path}, exists: {_theme_path.exists()}"
        )
        if not _theme_path.exists():
            logger.warning(f"Gameplay theme not found. CWD: {os.getcwd()}")

        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height),
            theme_path=str(_theme_path) if _theme_path.exists() else None,
        )
        self.dt = 0.0

        # Runtime attributes
        self.render_system: "RenderSystem | None" = None
        self.day_night_system: "DayNightSystem | None" = None
        self.hud: "HUD | None" = None
        self.hud_surface: pygame.Surface | None = None
        self.hud_texture: Any = None  # pl2d.Texture at runtime

        # Services and Systems
        self.game_config: Any = None
        self.camera: Camera
        self.audio: AudioManager
        self.physics_system: PhysicsSystem
        self.event_manager: EventManager
        self.event_bus: Any
        self.input_manager: InputManager
        self.loader: GameLoader
        self.economy_service: EconomyService
        self.time_service: TimeService
        self.settings_service: SettingsService
        self.game_service: GameService
        self.serializer: WorldSerializer
        self.input_system: Any

    def on_enter(self) -> None:
        """
        Called when the scene becomes active.

        Sets up the UI resolution.
        """
        logger.info("Entered Gameplay Scene")
        # setup is called by SceneManager before on_enter
        self.ui_manager.set_window_resolution(
            (self.application.width, self.application.height)
        )

    def setup(self, context: SceneContext) -> None:
        """
        Sets up the game environment.

        Initializes systems, services, and loads content.

        Args:
            context (SceneContext): Context data passed from the previous scene.
        """
        # Load Config
        self.game_config = load_config()

        self.camera = Camera(settings=self.game_config.world)
        self.audio = AudioManager()
        self.audio.load_from_config()

        self.physics_system = PhysicsSystem()
        self.event_manager = EventManager()
        self.event_bus = self.event_manager.bus
        self.input_manager = self.world.services.get(InputManager)
        self.input_manager.switch_context(InputContext.GAMEPLAY)

        # Initialize Loader
        self.loader = GameLoader(self.world, self.application, self.game_config)

        # Register services
        self.loader.register_services(
            context, self.audio, self.camera, self.physics_system, self.event_bus
        )

        # Cache service references for local usage
        self.economy_service = self.world.services.get(EconomyService)
        self.time_service = self.world.services.get(TimeService)
        self.settings_service = self.world.services.get(SettingsService)

        self._apply_initial_settings()

        # Factories
        self.loader.register_factories_and_managers()
        self.game_service = self.world.services.get(GameService)

        # Serializer
        self.serializer = WorldSerializer(
            self.world, self.loader.collect_component_types()
        )

        # Systems
        self.input_system = self.loader.register_systems(
            self.camera, self.event_bus, self.physics_system, self.ui_manager
        )

        self.is_setup = True
        self._setup_event_handlers()

        # Initial population if empty.
        if not self.application.headless and len(self.world.get_all_entities()) == 0:
            start_x = float(self.camera.width) / 2.0
            start_y = float(self.camera.height) / 2.0
            create_yukkuri(self.world, "reimu", start_x, start_y)
            self.camera.camera_x = float(start_x)
            self.camera.camera_y = float(start_y)

        # Headless mode intentionally skips auto-population for test control.

    def _apply_initial_settings(self) -> None:
        """Applies initial settings from the SettingsService."""
        audio_settings = self.settings_service.settings.audio
        self.audio.set_master_volume(audio_settings.master_volume)
        self.audio.set_bgm_volume(audio_settings.bgm_volume)
        self.audio.set_sfx_volume(audio_settings.sfx_volume)

    def _setup_event_handlers(self) -> None:
        """Sets up event subscriptions and initializes render-dependent systems."""
        # If running headlessly (tests), we skip rendering systems to avoid opening a window.
        if not self.application.headless and self.application.screen:
            self.render_system = RenderSystem(
                self.application.screen,
                self.world,
                lights_engine=getattr(self.application, "lights_engine", None),
            )

            # Day/Night System
            if TYPE_CHECKING:
                from ..game.systems.day_night import DayNightSystem
            else:
                try:
                    from ..game.systems.day_night import DayNightSystem
                except ImportError:
                    DayNightSystem = None  # Should not happen in normal run

            if DayNightSystem is not None:
                self.day_night_system = DayNightSystem(self.world, self.render_system)
                self.world.add_system(self.day_night_system)

            # HUD
            self.hud = HUD(self.ui_manager, self.world)

            # Initialize navigation debug renderer
            nav_service = self.world.services.try_get(NavigationService)
            if nav_service:
                self.hud.init_navigation_debug(nav_service, self.camera)

            # Initialize AI Debug
            self.hud.init_ai_debug(self.camera)

        # Logic Event Handlers (Must run even in headless mode)
        self.event_bus.subscribe(TogglePauseRequest, lambda e: self.toggle_pause())
        self.event_bus.subscribe(CycleSpeedRequest, lambda e: self.cycle_speed())
        self.event_bus.subscribe(ResolutionChangedEvent, self.on_resolution_changed)
        self.event_bus.subscribe(SaveGameRequest, lambda e: self.save(e.filename))
        self.event_bus.subscribe(LoadGameRequest, lambda e: self.load(e.filename))

    def on_exit(self) -> None:
        """
        Called when the scene is exited.

        Clears UI, shuts down services, and syncs global state.
        """
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()  # type: ignore[no-untyped-call]

        # Cleanup HUD listeners
        if self.hud:
            self.hud.cleanup()
            self.hud = None

        # Sync back global state to Application/SceneManager
        if hasattr(self, "economy_service") and self.economy_service:
            self.application.scene_manager.set_global_data(
                "money", self.economy_service.money
            )
        if hasattr(self, "time_service") and self.time_service:
            self.application.scene_manager.set_global_data(
                "time", self.time_service.time_elapsed
            )

        # Shutdown Navigation Service
        nav_service = self.world.services.try_get(NavigationService)
        if nav_service:
            nav_service.shutdown()
        else:
            logger.warning("NavigationService NOT found in on_exit.")

        # Clear local audio resources
        if hasattr(self, "audio") and self.audio:
            self.audio.clear()

        # Cleanup Event Bus to break reference cycles
        # This removes all subscribers, including the lambdas capturing 'self'
        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.clear()

    def toggle_pause(self) -> None:
        """Toggles the pause state."""
        self.paused = not self.paused
        self.event_bus.publish(GamePausedEvent(self.paused))

    def cycle_speed(self) -> None:
        """Cycles through game speed multipliers (1.0 -> 2.0 -> 5.0 -> 0.5)."""
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0
        self.time_scale = speeds[next_idx]
        if (
            self.hud
            and hasattr(self.hud, "layout")
            and self.hud.layout
            and self.hud.layout.speed_btn
        ):
            self.hud.layout.speed_btn.set_text(f"{self.time_scale}x")

    def on_resolution_changed(self, event: ResolutionChangedEvent) -> None:
        """
        Handles resolution change event.

        Args:
            event (ResolutionChangedEvent): The event data.
        """
        if self.application.headless:
            return

        # Delegate resolution change to Application which handles LightingEngine lifecycle
        self.application.change_resolution(event.width, event.height, event.fullscreen)

        # Re-initialize RenderSystem to use the new LightingEngine instance
        # and update screen references.
        if hasattr(self, "render_system") and self.application.screen:
            self.render_system = RenderSystem(
                self.application.screen,
                self.world,
                lights_engine=getattr(self.application, "lights_engine", None),
            )
            # Update DayNightSystem renderer reference
            if hasattr(self, "day_night_system") and self.day_night_system:
                self.day_night_system.render_system = self.render_system

        # Update local UI Manager
        self.ui_manager.set_window_resolution((event.width, event.height))

        # Update HUD layout
        if self.hud:
            self.hud.resize(event.width, event.height)

        # Invalidate hud_surface to force recreation in render()
        if hasattr(self, "hud_surface"):
            del self.hud_surface
            # Also ensure texture is cleared
            if hasattr(self, "hud_texture"):
                # Texture is from old context, so it's invalid anyway, but good to clean ref
                del self.hud_texture

    def take_screenshot(self) -> None:
        """Takes a screenshot and saves it to the screenshots directory."""
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = (
            f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        if self.application.screen:
            pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def save(self, filepath: str) -> None:
        """
        Saves the game state (Level + Global).

        Saves entity data to a msgpack file and global state to a JSON sidecar.

        Args:
            filepath (str): The base filepath for saving.
        """
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Save Level Data
        self.serializer.save_to_file(level_path)

        # Save Global Data
        global_data = {
            "money": self.economy_service.money,
            "time": self.time_service.time_elapsed,
        }
        with open(global_path, "w") as f:
            json.dump(global_data, f)

        logger.info(f"Game saved to {level_path} and {global_path}")

    def load(self, filepath: str) -> None:
        """
        Loads the game world from files.

        Args:
            filepath (str): The base filepath to load from.
        """
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Check files
        if not os.path.exists(level_path) or not os.path.exists(global_path):
            logger.error(f"Save files not found: {level_path} or {global_path}")
            return

        # Clear World
        self.world.clear_database()
        # Physics system clears itself via WorldClearedEvent

        self.camera.clear()

        # Reset Navigation Service
        nav_service = self.world.services.try_get(NavigationService)
        if nav_service:
            nav_service.reset()

        # Load Global Data
        with open(global_path) as f:
            global_data = json.load(f)

        self.economy_service.set_money(global_data.get("money", 0))
        self.time_service.time_elapsed = global_data.get("time", 0.0)

        # Load Level Data
        self.serializer.load_from_file(level_path)

        # Reconstruct physics bodies
        reconstruct_physics(self.world)

        # Migrate Skills
        # Need to get SkillService properly since it was not stored in self explicitly in new setup
        from ..game.skill_service import SkillService

        skill_service = self.world.services.try_get(SkillService)

        if skill_service:
            # Iterate all YukkuriStats entities
            for ent, (_, _) in self.world.get_components_tuple(
                yukkuri_components.YukkuriStats, components.Transform
            ):
                skill_service.initialize_skills(ent)

        logger.info("World loaded.")

    def update(self, dt: float) -> None:
        """
        Updates the scene logic.

        Args:
            dt (float): Delta time in seconds.
        """
        self.dt = dt
        self.ui_manager.update(dt)

        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        # Calculate simulation delta time
        if not self.paused:
            sim_dt = dt * self.time_scale
            self.event_manager.process_phase(GamePhase.UPDATE)
        else:
            sim_dt = 0.0

        # Run world update with calculated sim_dt (0 if paused, allowing systems to run without advancing simulation)
        # This effectively pauses gameplay logic (movement, physics) while allowing engine updates (input, UI) to continue.
        self.world.update(sim_dt)

        # Camera should always update with real dt so panning/zoom works while paused
        self.camera.update(dt)

        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        if not self.application.headless:
            # Throttle FPS update to save redraws (every 0.25s)
            if self.hud:
                self.hud.fps_timer = getattr(self.hud, "fps_timer", 0.0) + dt
                if self.hud.fps_timer >= 0.25:
                    # Cast clock to Any since get_fps is valid but mypy might miss internal state
                    clock: Any = self.application.clock
                    self.hud.fps = clock.get_fps()
                    self.hud.fps_timer = 0.0

                self.hud.update(dt)

    def render(self, alpha: float) -> None:
        """
        Renders the scene.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        self.render_world(alpha)

        if not self.application.headless and self.hud and self.application.screen:
            self.hud.draw(self.application.screen)
            self.ui_manager.draw_ui(self.application.screen)

    def render_world(self, alpha: float) -> None:
        """
        Renders the game world entities.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        if hasattr(self, "render_system") and self.render_system:
            # Pass alpha instead of dt to render_system.update
            # RenderSystem.update expects (world, dt), but we re-purpose second arg for alpha
            self.render_system.update(self.world, alpha)

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handles input events.

        Args:
            event (pygame.event.Event): The Pygame event.
        """
        self.ui_manager.process_events(event)
        # InputManager processing is handled by Application
        # Camera input is now handled by InputSystem via process_input()

        if self.input_manager.is_action_just_pressed("toggle_pause"):
            self.toggle_pause()

        if self.input_manager.is_action_just_pressed("pause"):
            # Update global state before leaving
            self.application.scene_manager.set_global_data(
                "money", self.economy_service.money
            )
            self.application.scene_manager.set_global_data(
                "time", self.time_service.time_elapsed
            )

            from .main_menu import MainMenuScene

            self.application.scene_manager.replace(MainMenuScene(self.application))
            return

        if not self.application.headless:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                if self.hud:
                    self.hud.toggle_ai_debug()

            if self.input_manager.is_action_just_pressed("debug_toggle"):
                if self.input_manager.is_action_pressed("shift"):
                    # Shift+F3 -> Toggle Lighting Debug
                    if self.hud:
                        self.hud.toggle_lighting_debug()
                        if self.render_system and hasattr(
                            self.render_system, "renderer"
                        ):
                            renderer: Any = self.render_system.renderer
                            renderer.toggle_lighting_debug(self.hud.lighting_debug)
                elif self.input_manager.is_action_pressed("ctrl"):
                    # Ctrl+F3 -> Toggle Mouse Light
                    mouse_light = self.world.services.try_get(MouseLightSystem)
                    if mouse_light:
                        mouse_light.toggle()
                elif self.input_manager.is_action_pressed("alt"):
                    # Alt+F3 -> Toggle Navigation Debug
                    if self.hud:
                        self.hud.toggle_navigation_debug()
                else:
                    if self.hud:
                        self.hud.toggle_debug()
            elif self.input_manager.is_action_just_pressed("screenshot"):
                self.take_screenshot()
            elif self.input_manager.is_action_just_pressed("quicksave"):
                self.save("quicksave")
            elif self.input_manager.is_action_just_pressed("quickload"):
                self.load("quicksave")

            if self.hud:
                self.hud.process_event(event)

    def init_render_system_headless(self) -> None:
        """
        Initializes the render system in headless mode for screenshots/verification.
        """
        # Always re-initialize or create if missing to ensure fresh state for screenshot
        # But we must be careful not to destroy existing state if it's fine.
        # Actually, RenderSystem is stateless except for screen reference.
        if (
            not hasattr(self, "render_system") or self.render_system is None
        ) and self.application.screen:
            self.render_system = RenderSystem(
                self.application.screen,
                self.world,
                lights_engine=getattr(self.application, "lights_engine", None),
            )
