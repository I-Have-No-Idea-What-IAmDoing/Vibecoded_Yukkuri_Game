import os
import sys
import psutil
import gc
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yukkuri_game.engine.application import Application
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.game.prefabs.yukkuri import create_yukkuri


def get_process_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def run_benchmark():
    logger.info("Starting Memory Benchmark...")

    # Initialize Headless Application
    app = Application(headless=True)

    initial_mem = get_process_memory_mb()
    logger.info(f"Initial Memory: {initial_mem:.2f} MB")

    cycles = 5
    entities_per_cycle = 50

    for i in range(cycles):
        logger.info(f"--- Cycle {i + 1}/{cycles} ---")

        # Push Gameplay Scene
        scene = GameplayScene(app)
        app.scene_manager.push(scene)

        # Simulate loading
        start_scene_mem = get_process_memory_mb()

        # Spawn Entities
        world = scene.world
        for _ in range(entities_per_cycle):
            create_yukkuri(world, "reimu", 0, 0)

        spawn_mem = get_process_memory_mb()
        logger.info(
            f"  Memory after spawn: {spawn_mem:.2f} MB (+{spawn_mem - start_scene_mem:.2f} MB)"
        )

        # Run some updates
        for _ in range(60):
            app.update(1.0 / 60.0)

        update_mem = get_process_memory_mb()

        # Pop Scene (should trigger cleanup and GC)
        app.scene_manager.pop()

        # Explicit GC for benchmark accuracy (though SceneManager.pop now does it)
        gc.collect()

        end_cycle_mem = get_process_memory_mb()
        logger.info(f"  Memory after cleanup: {end_cycle_mem:.2f} MB")
        logger.info(
            f"  Net change this cycle: {end_cycle_mem - start_scene_mem:.2f} MB"
        )

    final_mem = get_process_memory_mb()
    logger.info(f"Final Memory: {final_mem:.2f} MB")
    logger.info(f"Total Growth: {final_mem - initial_mem:.2f} MB")

    app.quit()


if __name__ == "__main__":
    run_benchmark()
