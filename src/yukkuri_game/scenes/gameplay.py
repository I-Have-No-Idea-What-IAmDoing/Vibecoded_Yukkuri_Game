"""
Gameplay Scene.
"""

import os
from datetime import datetime
from typing import ClassVar, Dict, Type

import pygame
import pygame_gui
from loguru import logger

from ..config import load_config
from ..engine.application import Application
from ..engine.audio import AudioManager
from ..engine.event_manager import EventManager, GamePhase
from ..engine.input_manager import InputContext, InputManager
from ..engine.scene import Scene, SceneContext
from ..engine.serializer import WorldSerializer
from ..game import components, yukkuri_components
from ..game.events import (
    CycleSpeedRequest,
    LoadGameRequest,
    ResolutionChangedEvent,
    SaveGameRequest,
    TogglePauseRequest,
)
from ..game.loader import GameLoader
from ..game.prefabs.yukkuri import create_yukkuri
from ..game.services import EconomyService, GameService, TimeService
from ..game.settings_service import SettingsService
from ..game.systems.physics import PhysicsSystem
from ..game.systems.physics_reconstruction import reconstruct_physics
from ..game.systems.render_system import RenderSystem
from ..game.ui.hud import HUD
from ..game.camera import Camera


class GameplayScene(Scene):
    """
    The main gameplay scene.
    Manages the game world, systems, and UI.
    """

    INJECTIONS: ClassVar[Dict[str, Type]] = {"money": int, "time": float}

    def __init__(self, application: Application):
        super().__init__(application)
        self.is_setup = False
        self.paused = False
        self.time_scale = 1.0
        self.ui_manager = pygame_gui.UIManager(
            (self.application.width, self.application.height)
        )
        self.dt = 0.0

    def on_enter(self) -> None:
        logger.info("Entered Gameplay Scene")
        # setup is called by SceneManager before on_enter
        self.ui_manager.set_window_resolution(
            (self.application.width, self.application.height)
        )

    def setup(self, context: SceneContext) -> None:
        """Sets up the game environment."""
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

        # Initial Population if empty
        if not self.application.headless and len(self.world.get_all_entities()) == 0:
            start_x = float(self.camera.width) / 2.0
            start_y = float(self.camera.height) / 2.0
            create_yukkuri(self.world, "reimu", start_x, start_y)
            self.camera.camera_x = float(start_x)
            self.camera.camera_y = float(start_y)

    def _apply_initial_settings(self) -> None:
        audio_settings = self.settings_service.settings.audio
        self.audio.set_master_volume(audio_settings.master_volume)
        self.audio.set_bgm_volume(audio_settings.bgm_volume)
        self.audio.set_sfx_volume(audio_settings.sfx_volume)

    def _setup_event_handlers(self) -> None:
        if not self.application.headless:
            self.render_system = RenderSystem(self.application.screen, self.world)
            self.hud = HUD(self.ui_manager, self.world)

            self.event_bus.subscribe(TogglePauseRequest, lambda e: self.toggle_pause())
            self.event_bus.subscribe(CycleSpeedRequest, lambda e: self.cycle_speed())
            self.event_bus.subscribe(ResolutionChangedEvent, self.on_resolution_changed)
            self.event_bus.subscribe(SaveGameRequest, lambda e: self.save(e.filename))
            self.event_bus.subscribe(LoadGameRequest, lambda e: self.load(e.filename))

    def on_exit(self) -> None:
        logger.info("Exited Gameplay Scene")
        self.ui_manager.clear_and_reset()

        # Sync back global state to Application/SceneManager
        if hasattr(self, "economy_service"):
            self.application.scene_manager.set_global_data(
                "money", self.economy_service.get_money()
            )
        if hasattr(self, "time_service"):
            self.application.scene_manager.set_global_data(
                "time", self.time_service.time_elapsed
            )

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def cycle_speed(self) -> None:
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
        if self.application.headless:
            return

        self.application.width = event.width
        self.application.height = event.height

        surface = pygame.display.get_surface()
        if surface:
            self.application.screen = surface
            self.render_system.screen = surface

        self.ui_manager.set_window_resolution((event.width, event.height))
        if self.hud:
            self.hud.resize(event.width, event.height)

    def take_screenshot(self) -> None:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = (
            f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        pygame.image.save(self.application.screen, filename)
        logger.info(f"Screenshot saved to {filename}")

    def save(self, filepath: str) -> None:
        """
        Save the game state (Level + Global).
        We'll save global state to a sidecar file or handle it via SceneManager.
        To keep it simple per requirements:
        - Save entities using WorldSerializer (msgpack)
        - Save global state (money, time) to json sidecar
        """
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Save Level Data
        self.serializer.save_to_file(level_path)

        # Save Global Data
        import json

        global_data = {
            "money": self.economy_service.get_money(),
            "time": self.time_service.time_elapsed,
        }
        with open(global_path, "w") as f:
            json.dump(global_data, f)

        logger.info(f"Game saved to {level_path} and {global_path}")

    def load(self, filepath: str) -> None:
        """Load the game world."""
        base_path, _ = os.path.splitext(filepath)
        global_path = base_path + ".global.json"
        level_path = base_path + ".level.msgpack"

        # Check files
        if not os.path.exists(level_path) or not os.path.exists(global_path):
            logger.error(f"Save files not found: {level_path} or {global_path}")
            return

        # Clear World
        self.world.clear_database()
        if hasattr(self, "physics_system"):
            self.physics_system.clear()
        self.camera.clear()

        # Load Global Data
        import json

        with open(global_path, "r") as f:
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
        self.dt = dt
        self.ui_manager.update(dt)

        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        if not self.paused:
            sim_dt = dt * self.time_scale
            if hasattr(self, "time_service"):
                self.time_service.time_elapsed += sim_dt

            self.event_manager.process_phase(GamePhase.UPDATE)
            self.world.update(sim_dt)
            self.camera.update(sim_dt)

        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        if not self.application.headless:
            self.hud.fps = self.application.clock.get_fps()
            self.hud.update(dt)

    def render(self) -> None:
        self.render_world()

        if not self.application.headless:
            self.hud.draw(self.application.screen)
            self.ui_manager.draw_ui(self.application.screen)

    def render_world(self) -> None:
        if hasattr(self, "render_system") and self.render_system:
            alpha = 1.0
            if hasattr(self.application, "accumulator") and hasattr(
                self.application, "fixed_dt"
            ):
                alpha = self.application.accumulator / self.application.fixed_dt
                # Clamp alpha just in case
                alpha = max(0.0, min(1.0, alpha))

            # Pass alpha instead of dt to render_system.update
            # RenderSystem.update expects (world, dt), but we re-purpose second arg for alpha
            self.render_system.update(self.world, alpha)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.ui_manager.process_events(event)
        # InputManager processing is handled by Application

        if hasattr(self, "camera"):
            self.camera.handle_input(
                event, self.application.width, self.application.height
            )

        if self.input_manager.is_action_just_pressed("pause"):
            # Update global state before leaving
            self.application.scene_manager.set_global_data(
                "money", self.economy_service.get_money()
            )
            self.application.scene_manager.set_global_data(
                "time", self.time_service.time_elapsed
            )

            from .main_menu import MainMenuScene

            self.application.scene_manager.replace(MainMenuScene(self.application))
            return

        if not self.application.headless:
            if self.input_manager.is_action_just_pressed("debug_toggle"):
                self.hud.toggle_debug()
            elif self.input_manager.is_action_just_pressed("screenshot"):
                self.take_screenshot()
            elif self.input_manager.is_action_just_pressed("quicksave"):
                self.save("quicksave")
            elif self.input_manager.is_action_just_pressed("quickload"):
                self.load("quicksave")

            self.hud.process_event(event)
