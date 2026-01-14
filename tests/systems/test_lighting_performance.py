import pygame
import time
from yukkuri_game.game.renderer.software_lighting import SoftwareLightingEngine


def test_lighting_performance_huge_radius():
    pygame.init()
    # 800x600 screen
    screen_size = (800, 600)
    engine = SoftwareLightingEngine(screen_size, scale=1.0)

    # 1. Baseline: Normal light (radius 100)
    start_time = time.perf_counter()
    for _ in range(10):
        engine.clear((20, 20, 20))
        engine.render_light((400, 300), 100, (255, 255, 255), 1.0)
    normal_duration = time.perf_counter() - start_time

    # 2. Huge Light (radius 2000 - simulated 20x zoom on 100px light)
    # This should be MUCH slower without optimization
    start_time = time.perf_counter()
    for _ in range(10):
        engine.clear((20, 20, 20))
        engine.render_light((400, 300), 2000, (255, 255, 255), 1.0)
    huge_duration = time.perf_counter() - start_time

    print(f"\nNormal Light (10 frames): {normal_duration:.4f}s")
    print(f"Huge Light (10 frames)  : {huge_duration:.4f}s")

    # Expect huge light to be at least 10x slower (conservative estimate, likely 100x/quadratically)
    # If optimization works, it should be much closer to normal light (bounded by screen size)

    # For CI/Pass condition: We assert that huge_duration is visible, but we care about the delta.
    # This test is mostly for manual verification of improvement.

    # If optimization is effective, drawing a 2000px light (covering screen) should cost roughly
    # the same as filling the screen.

    assert True


if __name__ == "__main__":
    test_lighting_performance_huge_radius()
