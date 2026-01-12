
import cProfile
import pstats
import argparse
from src.yukkuri_game.engine.application import Application
from src.yukkuri_game.scenes.main_menu import MainMenuScene
from src.yukkuri_game.scenes.gameplay import GameplayScene
import pygame
import sys

# Mock pygame.event.get to simulate quit after some time
# Or we can just run for N frames in the loop

class ProfiledApplication(Application):
    def __init__(self, headless=True, duration_frames=300):
        super().__init__(headless=headless)
        self.duration_frames = duration_frames
        self.frame_count = 0

    def run(self):
        """Override run to stop after N frames."""
        print(f"Profiling for {self.duration_frames} frames...")

        while self.running and self.frame_count < self.duration_frames:
            # Main Loop Steps
            dt = self.clock.tick(60) / 1000.0
            self.frame_count += 1

            # Events
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                self.ui_manager.process_events(event)

            # Update
            self.scene_manager.update(dt)
            self.ui_manager.update(dt)

            # Draw
            if self.scene_manager.current_scene:
                self.scene_manager.render()

            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

        print("Profiling finished.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="profile.stats")
    parser.add_argument("--frames", type=int, default=300)
    args = parser.parse_args()

    profiler = cProfile.Profile()

    app = ProfiledApplication(headless=True, duration_frames=args.frames)
    # Push Gameplay Scene directly to test game loop
    app.scene_manager.push(GameplayScene(app))

    profiler.enable()
    app.run()
    profiler.disable()

    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.dump_stats(args.output)
    print(f"Profile saved to {args.output}")

if __name__ == "__main__":
    main()
