import time
import pygame
from src.yukkuri_game.game.renderer_new.shadow_caster import ShadowCaster
from src.yukkuri_game.game.renderer_new.native_light_backend import NativeLightBackend
from src.yukkuri_game.game.renderer_new.commands import LightCommand, OccluderCommand

def benchmark_lighting(num_lights: int, num_occluders: int, iterations: int = 100):
    pygame.init()
    # Dummy screen
    screen = pygame.Surface((1920, 1080))
    backend = NativeLightBackend(screen)

    # Setup Scene
    # Random occluders
    import random
    random.seed(42)

    backend.begin_frame()

    # Create Occluders
    occluder_vertices_list = []

    for i in range(num_occluders):
        x = random.randint(0, 1900)
        y = random.randint(0, 1060)
        w = random.randint(20, 50)
        h = random.randint(20, 50)
        verts = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]

        backend.draw_occluder(OccluderCommand(
            layer=0, z_index=0, entity_id=i,
            vertices=verts,
            static=True
        ))
        # Calculate AABB for the benchmark list manually to match backend structure
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        aabb = (min(xs), max(xs), min(ys), max(ys))
        occluder_vertices_list.append((aabb, verts))

    # Create Lights
    lights = []
    for i in range(num_lights):
        lights.append(LightCommand(
            layer=1, z_index=0, entity_id=i + 1000,
            position=(random.randint(0, 1920), random.randint(0, 1080)),
            radius=300,
            color=(255, 200, 150, 255),
            intensity=1.0
        ))
        backend.draw_light(lights[-1])

    # Measure
    caster = ShadowCaster()

    # We want to measure the time taken for the "lighting pass" specifically,
    # which is mostly calculate_visibility_polygon calls inside end_frame (or internal logic).
    # Since NativeLightBackend does everything in end_frame, let's measure that.
    # Note: drawing sprites is fast, we care about the light loop.

    start_time = time.perf_counter()

    for _ in range(iterations):
        # We need to simulate the loop in NativeLightBackend._render_light mostly
        for light in lights:
             caster.calculate_visibility_polygon(light.position, light.radius, occluder_vertices_list)

    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time_per_frame = (total_time / iterations) * 1000 # ms

    print(f"Benchmark Results:")
    print(f"Lights: {num_lights}, Occluders: {num_occluders}")
    print(f"Total Time ({iterations} iters): {total_time:.4f} s")
    print(f"Avg Time per Frame (Shadow Calculation Only): {avg_time_per_frame:.2f} ms")

    # Also estimate full backend overhead
    start_time = time.perf_counter()
    for _ in range(iterations):
        backend.end_frame()
        # Note: end_frame accumulates draws to screen, so it might get slower or fill surface.
        # But we are drawing to an offscreen surface.
    end_time = time.perf_counter()
    total_time_full = end_time - start_time
    avg_time_per_frame_full = (total_time_full / iterations) * 1000

    print(f"Avg Time per Frame (Full Render Pipeline): {avg_time_per_frame_full:.2f} ms")

if __name__ == "__main__":
    # Test cases
    print("--- Scenario 1: Light Load ---")
    benchmark_lighting(num_lights=5, num_occluders=10, iterations=50)

    print("\n--- Scenario 2: Medium Load ---")
    benchmark_lighting(num_lights=20, num_occluders=50, iterations=20)

    print("\n--- Scenario 3: Heavy Load ---")
    benchmark_lighting(num_lights=50, num_occluders=100, iterations=10)
