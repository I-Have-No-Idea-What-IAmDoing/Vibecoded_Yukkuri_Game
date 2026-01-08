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

    # Create Occluders
    occluder_vertices_list = []

    # We must call begin_frame to reset lists
    backend.begin_frame()

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

        # Keep track for direct caster comparison
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        aabb = (min(xs), max(xs), min(ys), max(ys))
        occluder_vertices_list.append((aabb, verts))

    # Create Lights
    lights = []
    for i in range(num_lights):
        l = LightCommand(
            layer=1, z_index=0, entity_id=i + 1000,
            position=(random.randint(0, 1920), random.randint(0, 1080)),
            radius=300,
            color=(255, 200, 150, 255),
            intensity=1.0
        )
        lights.append(l)
        backend.draw_light(l)

    print(f"Benchmark Results:")
    print(f"Lights: {num_lights}, Occluders: {num_occluders}")

    # Measure Uncached (Direct Call to ShadowCaster)
    caster = ShadowCaster()
    start_time = time.perf_counter()
    for _ in range(iterations):
        for light in lights:
             caster.calculate_visibility_polygon(light.position, light.radius, occluder_vertices_list)
    end_time = time.perf_counter()
    avg_uncached = ((end_time - start_time) / iterations) * 1000
    print(f"Avg Time per Frame (Uncached Direct): {avg_uncached:.2f} ms")

    # Measure Cached (Backend)
    # The first frame will populate the cache, subsequent frames should be fast.

    # Warmup (Populate Cache)
    backend.end_frame()

    # Now run benchmark using backend
    # Note: We need to re-submit commands every frame because begin_frame clears them.
    # But checking cache happens inside end_frame using entity_id.

    start_time = time.perf_counter()
    for _ in range(iterations):
        backend.begin_frame()
        # Re-submit occluders (simulating game loop)
        for i in range(num_occluders):
             # We need to recreate commands or reuse them.
             # In game loop, systems create new commands usually.
             # But backend relies on ID match.
             # We must ensure we pass the SAME IDs.
             pass
             # Wait, draw_occluder clears occluders list.
             # We need to re-add them.

        # Optimization for benchmark: just manually re-add internal lists if possible,
        # or call draw_occluder.

        for i in range(num_occluders):
            # Using same seed/logic implies same geometry, so static cache should hold.
            # But here we used random earlier.
            # Let's just use the verts we stored.
            (aabb, verts) = occluder_vertices_list[i]
            backend.draw_occluder(OccluderCommand(
                layer=0, z_index=0, entity_id=i,
                vertices=verts,
                static=True
            ))

        for l in lights:
            backend.draw_light(l)

        backend.end_frame()

    end_time = time.perf_counter()
    avg_cached = ((end_time - start_time) / iterations) * 1000
    print(f"Avg Time per Frame (Cached Backend): {avg_cached:.2f} ms")

    speedup = avg_uncached / avg_cached if avg_cached > 0 else 0
    print(f"Speedup: {speedup:.2f}x")

if __name__ == "__main__":
    # Test cases
    print("--- Scenario 1: Light Load ---")
    benchmark_lighting(num_lights=5, num_occluders=10, iterations=50)

    print("\n--- Scenario 2: Medium Load ---")
    benchmark_lighting(num_lights=20, num_occluders=50, iterations=20)

    print("\n--- Scenario 3: Heavy Load ---")
    benchmark_lighting(num_lights=50, num_occluders=100, iterations=10)
