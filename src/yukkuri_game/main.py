import sys
import os
from datetime import datetime
import argparse
import pygame
from .engine.core import GameLoop
from .engine.audio import AudioManager
from .game.yukkurrium import Yukkurrium, RenderSystem, TimeSystem
from .game.game_manager import GameManager
from .game.entity_factory import EntityFactory
from .game.ai.utility import UtilityAIEngine
from .game.systems.simulation import YukkuriAISystem
from .game.ui.hud import HUD
from .game.input_system import InputSystem
from .game.yukkuri_components import AIState # Fix import for HUD string check if needed

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
        """
        # Systems
        self.yukkurrium = Yukkurrium(width=3000, height=3000)
        self.audio = AudioManager()

        # Factory & Game Manager
        self.factory = EntityFactory(self.world, self.resources)
        self.gm = GameManager(self.world, self.factory)

        # AI
        self.ai_engine = UtilityAIEngine(self.resources)

        # Add Systems (Processors in esper)
        self.input_system = InputSystem(self.yukkurrium)
        self.world.add_processor(self.input_system) # Update doesn't do much, events handled separately

        self.world.add_processor(TimeSystem())
        self.world.add_processor(YukkuriAISystem(self.ai_engine, float(self.yukkurrium.width), float(self.yukkurrium.height)))

        if not self.headless:
            self.render_system = RenderSystem(self.screen, self.yukkurrium, self.resources)
            # RenderSystem is not added to world updates because it should be called in render_world
            # But RenderSystem is an esper.Processor now, so we could add it and control priority,
            # but we want to control WHEN it runs (during render_world).
            # esper.process() runs all processors.
            # We can manually call process on render_system instead of adding it to the world.
            # This is what we did before.

            # UI
            self.hud = HUD(self.ui_manager, self.gm, self.world, self.factory)
            # Callbacks are set in HUD init or handled via method binding if exposed
            # For this structure, we'll assume HUD has these methods or we need to pass them.
            # If HUD doesn't have these attributes defined in its class, we can't just assign them if strict typing is on.
            # Assuming we can assign for now or refactor HUD to accept them.
            self.hud.toggle_pause_callback = self.toggle_pause
            self.hud.cycle_speed_callback = self.cycle_speed
            self.hud.start_placement_callback = self.start_placement

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
        """
        if not self.headless:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.hud.toggle_debug()
                elif event.key == pygame.K_F12:
                    self.take_screenshot()

            self.input_system.handle_event(event, self.width, self.height, self.ui_manager)
            self.hud.process_event(event)

    def update(self) -> None:
        """
        Updates the game state each frame.

        Advances time in the GameManager and updates the Yukkurrium (camera).
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
        """
        if not self.headless and self.render_system:
            # Manually run the render system
            # We need to set the world for the processor if we didn't add it to the world?
            # esper.Processor.world is set when added to world.
            # But we are not adding it. We can manually set it or just pass it if we kept the old signature?
            # No, I changed the signature to process(dt).
            # So I need to set .world manually.
            self.render_system.world = self.world
            self.render_system.process(self.dt)

    def toggle_pause(self) -> None:
        """
        Toggles the paused state of the simulation.
        """
        self.paused = not self.paused
        self.hud.pause_btn.set_text("Resume" if self.paused else "Pause")

    def cycle_speed(self) -> None:
        """
        Cycles through available game simulation speeds (1.0, 2.0, 5.0, 0.5).
        """
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0

        self.time_scale = speeds[next_idx]
        self.hud.speed_btn.set_text(f"{self.time_scale}x")

    def start_placement(self, type_id: str, cost: int, entity_type: str) -> None:
        """
        Initiates the placement mode for an entity.

        Args:
            type_id: The ID of the entity type.
            cost: The cost of the entity.
            entity_type: The category ("yukkuri" or "item").
        """
        self.input_system.start_placement(type_id, cost, entity_type, self.gm, self.factory)

    def take_screenshot(self) -> None:
        """
        Captures a screenshot and saves it to the 'screenshots' directory.
        """
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pygame.image.save(self.screen, filename)
        print(f"Screenshot saved to {filename}")

def main():
    """
    The entry point for the application.

    Parses command-line arguments and starts the game loop.
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
