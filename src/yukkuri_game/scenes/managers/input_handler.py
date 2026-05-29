"""
Gameplay Input Handler.

Processes input events and translates them into appropriate
gameplay actions or UI updates.
"""

from typing import TYPE_CHECKING, Any

import pygame

from loguru import logger

from ...engine.input_manager import InputManager
from ...game.systems.mouse_light_system import MouseLightSystem

if TYPE_CHECKING:
    from ...scenes.gameplay import GameplayScene
    from .game_session import GameSessionManager


class GameplayInputHandler:
    """
    Handles input events for the GameplayScene.

    Attributes:
        scene (GameplayScene): The owning scene.
        session (GameSessionManager): The session manager.
        input_manager (InputManager): The input manager service.
    """

    def __init__(
        self,
        scene: "GameplayScene",
        session: "GameSessionManager",
        input_manager: InputManager,
    ) -> None:
        """
        Initializes the input handler.

        Args:
            scene (GameplayScene): The owning scene.
            session (GameSessionManager): The session manager.
            input_manager (InputManager): The engine's input manager.
        """
        self.scene = scene
        self.session = session
        self.input_manager = input_manager

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Processes a single pygame event.

        Args:
            event (pygame.event.Event): The event to process.
        """
        # Let the UI manager process first
        self.scene.ui_manager.process_events(event)

        # Global input shortcuts via InputManager
        if self.input_manager.is_action_just_pressed("toggle_pause"):
            self.session.toggle_pause()

        if self.input_manager.is_action_just_pressed("pause"):
            # Update global state before leaving
            self.scene.application.scene_manager.set_global_data(
                "money", self.scene.economy_service.money
            )
            self.scene.application.scene_manager.set_global_data(
                "time", self.scene.time_service.time_elapsed
            )

            from ...scenes.main_menu import MainMenuScene

            self.scene.application.scene_manager.replace(
                MainMenuScene(self.scene.application)
            )
            return

        # Skip developer/debug shortcuts if headless
        if not self.scene.application.headless:
            self._handle_debug_shortcuts(event)

            # Pass event to HUD
            if self.scene.hud:
                self.scene.hud.process_event(event)

    def _handle_debug_shortcuts(self, event: pygame.event.Event) -> None:
        """Handles developer and debug shortcuts."""
        # F4: Legacy AI Debug Toggle
        # Ctrl+F4: Toggle physics debug
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            if event.mod & pygame.KMOD_CTRL:
                if self.scene.hud:
                    self.scene.hud.toggle_physics_debug()
                    state = "OFF"
                    if self.scene.hud.physics_debug_renderer:
                        state = (
                            "ON"
                            if self.scene.hud.physics_debug_renderer.enabled
                            else "OFF"
                        )
                    logger.info("Physics debug visuals: {}", state)
            else:
                if self.scene.hud:
                    self.scene.hud.toggle_ai_debug()

        # F5: Toggle per-system timing (world.debug_timing)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            self.scene.world.debug_timing = (
                not self.scene.world.debug_timing
            )
            state = "ON" if self.scene.world.debug_timing else "OFF"
            logger.info("Per-system timing: {}", state)

        # F6: World Dump (lists all entities + their components)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
            logger.info("=== ECS WORLD DUMP ===")
            for entity in self.scene.world.get_all_entities():
                comps = self.scene.world.get_all_components(entity)
                comp_names = [type(c).__name__ for c in comps]
                logger.info(
                    "  Entity {}: [{}]",
                    entity,
                    ", ".join(comp_names),
                )
            logger.info("======================")

        # F7: Scene Stack Dump
        # Ctrl+F7: Toggle event bus tracing
        # Shift+F7: Live dump of recent events buffer
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
            if event.mod & pygame.KMOD_CTRL:
                bus = getattr(self.scene, "event_bus", None)
                if bus is not None:
                    bus.trace = not bus.trace
                    state = "ON" if bus.trace else "OFF"
                    logger.info("EventBus tracing: {}", state)
            elif event.mod & pygame.KMOD_SHIFT:
                bus = getattr(self.scene, "event_bus", None)
                if bus is not None and bus.recent_events:
                    logger.info("=== LIVE EVENT REPLAY BUFFER DUMP ===")
                    for ev in bus.recent_events:
                        if isinstance(ev, dict):
                            from datetime import datetime
                            ts = datetime.fromtimestamp(
                                ev["timestamp"]
                            ).strftime("%H:%M:%S.%f")[:-3]
                            logger.info(
                                "[{}] {}{}", ts, ev["type"], ev["payload"]
                            )
                        else:
                            logger.info("{}", ev)
                    logger.info("=====================================")
            else:
                stack_str = (
                    self.scene.application.scene_manager
                    .dump_scene_stack()
                )
                logger.info("=== SCENE STACK DUMP ===")
                logger.info(stack_str)
                logger.info("========================")

        if self.input_manager.is_action_just_pressed("debug_toggle"):
            if self.input_manager.is_action_pressed("shift"):
                # Shift+F3 -> Toggle Lighting Debug
                if self.scene.hud:
                    self.scene.hud.toggle_lighting_debug()
                    if self.scene.render_system and hasattr(
                        self.scene.render_system, "renderer"
                    ):
                        renderer: Any = self.scene.render_system.renderer
                        renderer.toggle_lighting_debug(self.scene.hud.lighting_debug)
            elif self.input_manager.is_action_pressed("ctrl"):
                # Ctrl+F3 -> Toggle Mouse Light
                mouse_light = self.scene.world.services.try_get(MouseLightSystem)
                if mouse_light:
                    mouse_light.toggle()
            elif self.input_manager.is_action_pressed("alt"):
                # Alt+F3 -> Toggle Navigation Debug
                if self.scene.hud:
                    self.scene.hud.toggle_navigation_debug()
            else:
                # F3 -> Generic UI Debug Toggle
                if self.scene.hud:
                    self.scene.hud.toggle_debug()

        elif self.input_manager.is_action_just_pressed("screenshot"):
            self.scene.take_screenshot()
        elif self.input_manager.is_action_just_pressed("quicksave"):
            if hasattr(self.scene, "save_manager"):
                self.scene.save_manager.save_game("quicksave")
        elif self.input_manager.is_action_just_pressed("quickload"):
            if hasattr(self.scene, "save_manager"):
                self.scene.save_manager.load_game(
                    "quicksave", camera=self.scene.camera
                )

        # [ / ] — Debug time-scale ladder (0.1x → 0.25x → 0.5x → 1x → 2x → 4x)
        _SPEED_LADDER = [0.1, 0.25, 0.5, 1.0, 2.0, 4.0]
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFTBRACKET:
            cur = self.session.time_scale
            try:
                idx = _SPEED_LADDER.index(cur)
            except ValueError:
                idx = _SPEED_LADDER.index(1.0)
            new_scale = _SPEED_LADDER[max(0, idx - 1)]
            self.session.time_scale = new_scale
            logger.info("Time scale: {}x", new_scale)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHTBRACKET:
            cur = self.session.time_scale
            try:
                idx = _SPEED_LADDER.index(cur)
            except ValueError:
                idx = _SPEED_LADDER.index(1.0)
            new_scale = _SPEED_LADDER[min(len(_SPEED_LADDER) - 1, idx + 1)]
            self.session.time_scale = new_scale
            logger.info("Time scale: {}x", new_scale)

        # Period (.) — Step-frame when paused
        if event.type == pygame.KEYDOWN and event.key == pygame.K_PERIOD:
            if self.session.paused:
                setattr(self.session, "_step_frame_requested", True)
                logger.info("Step-frame: advanced simulation by 1 frame")
