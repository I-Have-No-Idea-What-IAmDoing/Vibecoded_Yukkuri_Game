"""
Gameplay Input Handler.

Processes input events and translates them into appropriate
gameplay actions or UI updates.
"""

from typing import TYPE_CHECKING, Any

import pygame

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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            if self.scene.hud:
                self.scene.hud.toggle_ai_debug()

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
                self.scene.save_manager.load_game("quicksave", camera=self.scene.camera)
