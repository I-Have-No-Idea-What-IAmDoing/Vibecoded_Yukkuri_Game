import time
import pymunk
import sys
import os

# Add src to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import Transform, PhysicsBody
from yukkuri_game.engine.ecs import World


def run_benchmark():
    world = World()
    physics_system = PhysicsSystem(gravity=(0, 0))
    # Inject world into system manually
    physics_system.ecs_world = world
    physics_system.initialize()

    count = 5000
    print(f"Creating {count} entities...")
    for i in range(count):
        entity = world.create_entity()

        # Create dynamic body (mass=1, moment=1)
        body = pymunk.Body(1, 1)
        body.position = (i * 10.0, 0.0)
        shape = pymunk.Circle(body, 5)

        phys = PhysicsBody(body=body, shape=shape)
        trans = Transform(x=i * 10.0, y=0.0)

        world.add_component(entity, phys)
        world.add_component(entity, trans)
        physics_system.space.add(body, shape)

    frames = 600
    print(f"Running simulation for {frames} frames...")

    start_time = time.time()
    dt = 1.0 / 60.0

    for _ in range(frames):
        physics_system.update(world, dt)

    end_time = time.time()
    duration = end_time - start_time
    avg_tick = (duration / frames) * 1000

    print(f"Total time: {duration:.4f}s")
    print(f"Average tick: {avg_tick:.4f}ms")


if __name__ == "__main__":
    run_benchmark()
