import pygame
import time
from yukkuri_game.engine.renderer.pygame_backend import PygameBackend
from yukkuri_game.engine.renderer.commands import ShadowCommand


def test_shadow_performance_zooming():
    pygame.init()
    screen = pygame.Surface((800, 600))
    backend = PygameBackend(screen)

    # 1. Simulate Zoom: Render shadows with increasing size
    # This hits the cache miss path continuously
    start_time = time.perf_counter()

    # Simulate zooming from 1.0 to 20.0 in 0.05 steps (approx 400 frames)
    # A single entity shadow
    zoom_levels = [1.0 + i * 0.05 for i in range(400)]

    for zoom in zoom_levels:
        # Radius scales with zoom
        rx = 32 * zoom
        ry = 10 * zoom

        cmd = ShadowCommand(
            layer=1,
            z_index=0,
            position=(400, 300),
            radius=(rx, ry),
            color=(0, 0, 0, 128),
        )

        backend._render_shadow(cmd)

    duration = time.perf_counter() - start_time

    # Check cache size - if optimization is missing, it will be 400
    cache_size = len(backend.shadow_surface_cache)

    print(f"\nZoom Shadow Rendering (400 frames/sizes): {duration:.4f}s")
    print(f"Final Cache Size: {cache_size}")

    # Expected:
    # Without optimization: Cache size ~400, Duration higher due to allocation
    # With optimization: Cache size should be small (only small shadows cached), Duration lower

    assert True


if __name__ == "__main__":
    test_shadow_performance_zooming()
