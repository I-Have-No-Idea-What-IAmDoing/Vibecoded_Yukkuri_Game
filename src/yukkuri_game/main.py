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
    def setup(self):
        # Systems
        self.yukkurrium = Yukkurrium(width=3000, height=3000)
        self.audio = AudioManager()

        # Factory & Game Manager
        self.factory = EntityFactory(self.world, self.resources)
        self.gm = GameManager(self.world, self.factory)

        # AI
        self.ai_engine = UtilityAIEngine(self.resources)

        # Add Systems
        self.input_system = InputSystem(self.yukkurrium)
        self.world.add_system(self.input_system) # Update doesn't do much, events handled separately

        self.world.add_system(TimeSystem())
        self.world.add_system(YukkuriAISystem(self.ai_engine, self.yukkurrium.width, self.yukkurrium.height))

        if not self.headless:
            self.render_system = RenderSystem(self.screen, self.yukkurrium, self.resources)
            # RenderSystem is not added to world updates because it should be called in render_world
            # self.world.add_system(self.render_system)

            # UI
            self.hud = HUD(self.ui_manager, self.gm, self.world, self.factory)
            self.hud.toggle_pause_callback = self.toggle_pause
            self.hud.cycle_speed_callback = self.cycle_speed
            self.hud.start_placement_callback = self.start_placement

        # Initial Population
        if not self.headless:
            # Create a starting Reimu
            start_x = self.yukkurrium.width / 2
            start_y = self.yukkurrium.height / 2
            self.factory.create_yukkuri("reimu", start_x, start_y)

            # Center camera on start
            self.yukkurrium.camera_x = start_x
            self.yukkurrium.camera_y = start_y

    def on_event(self, event):
        if not self.headless:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.hud.toggle_debug()
                elif event.key == pygame.K_F12:
                    self.take_screenshot()

            self.input_system.handle_event(event, self.world, self.width, self.height)
            self.hud.process_event(event)

    def update(self):
        if not self.paused:
            self.gm.time_elapsed += self.dt * self.time_scale

        super().update()
        self.yukkurrium.update(self.dt)

        if not self.headless:
            self.hud.fps = self.clock.get_fps()
            self.hud.update(self.dt)

    def render_world(self):
        if not self.headless and self.render_system:
            self.render_system.update(self.world, self.dt)

    def toggle_pause(self):
        self.paused = not self.paused
        self.hud.pause_btn.set_text("Resume" if self.paused else "Pause")

    def cycle_speed(self):
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0

        self.time_scale = speeds[next_idx]
        self.hud.speed_btn.set_text(f"{self.time_scale}x")

    def start_placement(self, type_id, cost, entity_type):
        self.input_system.start_placement(type_id, cost, entity_type, self.gm, self.factory)

    def take_screenshot(self):
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pygame.image.save(self.screen, filename)
        print(f"Screenshot saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Yukkuri Raising Game")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no window)")
    args = parser.parse_args()

    game = YukkuriGame()
    if args.headless:
        game.set_headless(True)

    game.run()

if __name__ == "__main__":
    main()
