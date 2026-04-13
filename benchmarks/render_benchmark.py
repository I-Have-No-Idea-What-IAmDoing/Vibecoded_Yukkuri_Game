import sys
import os
import time
import random
import pygame

from yukkuri_game.engine.ecs import World  # noqa: E402
from yukkuri_game.game.systems.render_system import RenderSystem  # noqa: E402
from yukkuri_game.game.systems.sector_system import SectorSystem  # noqa: E402
from yukkuri_game.game.components import (
    Transform,
    FloatingText,
    Sprite,
    VisualTransform,
)  # noqa: E402
from yukkuri_game.game.camera import Camera  # noqa: E402
from yukkuri_game.game.services import TimeService  # noqa: E402
from yukkuri_game.engine.resource_manager import ResourceManager  # noqa: E402

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock pygame for headless environment if needed
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()


def setup_world(num_entities=5000, num_floating_text=1000):
    world = World()

    # Register Services
    screen = pygame.Surface((800, 600))
    world.services.register(TimeService())

    # Mock ResourceManager
    rm = ResourceManager()
    from yukkuri_game.engine.lazy_loader import LazyLoader

    # We need to mock load_image to return a surface
    rm.load_image = lambda name: pygame.Surface((32, 32))  # type: ignore
    rm.item_types = LazyLoader(lambda x: None)
    rm.yukkuri_types = LazyLoader(lambda x: None)
    world.services.register(rm)

    # Camera
    camera = Camera()
    world.services.register(camera)

    # Systems
    sector_system = SectorSystem(width=10000, height=10000)
    world.add_system(sector_system)

    render_system = RenderSystem(screen, world)
    world.add_system(render_system)

    # Populate World
    # Spread entities over 10000x10000 area
    # Camera sees 800x600 (roughly)

    print(f"Spawning {num_entities} entities...")
    for _ in range(num_entities):
        x = random.uniform(0, 10000)
        y = random.uniform(0, 10000)
        world.create_entity(
            Transform(x=x, y=y),
            Sprite(image_name="test.png", width=32, height=32),
            VisualTransform(),
        )

    print(f"Spawning {num_floating_text} floating texts...")
    for _ in range(num_floating_text):
        x = random.uniform(0, 10000)
        y = random.uniform(0, 10000)
        world.create_entity(
            Transform(x=x, y=y),
            FloatingText(
                text="Test",
                color=(255, 255, 255),
                lifetime=1.0,
                max_lifetime=1.0,
                velocity_y=10.0,
            ),
        )

    # Ensure SectorSystem updates
    sector_system.update(world, 0.1)

    return world, render_system


def run_benchmark():
    world, render_system = setup_world(num_entities=10000, num_floating_text=5000)

    # Run a few frames to warm up
    render_system.update(world, 0.016)

    print("Starting benchmark...")
    start_time = time.perf_counter()
    iterations = 100

    for _ in range(iterations):
        # We manually call _process_floating_text to isolate it,
        # OR we call update() to measure total impact.
        # Let's call update() to see real world impact,
        # but keep in mind render_system does other things.
        # Actually, let's measure _process_floating_text specifically if possible,
        # but modifying the method signature will break this benchmark script if we call it directly.
        # So we call update().

        render_system.update(world, 0.016)

    end_time = time.perf_counter()
    duration = end_time - start_time
    avg_time = duration / iterations * 1000  # ms

    print(f"Total time: {duration:.4f}s")
    print(f"Average frame time: {avg_time:.4f}ms")


if __name__ == "__main__":
    run_benchmark()
