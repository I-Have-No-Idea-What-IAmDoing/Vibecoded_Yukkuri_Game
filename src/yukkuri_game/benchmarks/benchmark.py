"""
Benchmarking utility for performance regression testing.
"""

import time
import sys
import argparse
from typing import Dict, Any, List
import statistics

from ..testing.driver import GameDriver
from ..testing.environment import TestEnvironment
from ..engine.application import Application
from ..scenes.gameplay import GameplayScene

# We need to ensure we can create entities.
# The GameDriver.create_yukkuri method relies on EntityFactory being present in the world.
# GameplayScene sets up the world and systems, so it should be fine.


class BenchmarkRunner:
    """
    Runs performance benchmarks for the game.
    """

    def __init__(self, num_entities: int = 100, duration_seconds: float = 10.0, iterations: int = 3):
        """
        Initializes the BenchmarkRunner.

        Args:
            num_entities (int): Number of entities to spawn.
            duration_seconds (float): Game time duration to simulate per iteration.
            iterations (int): Number of iterations to run.
        """
        self.num_entities = num_entities
        self.duration_seconds = duration_seconds
        self.iterations = iterations

    def run(self) -> Dict[str, Any]:
        """
        Runs the benchmark.

        Returns:
            Dict[str, Any]: The benchmark results.
        """
        fps_results: List[float] = []
        speed_ratio_results: List[float] = []

        print(f"Running benchmark with {self.num_entities} entities for {self.duration_seconds}s game time ({self.iterations} iterations)...")

        with TestEnvironment():
            for i in range(self.iterations):
                # Initialize Application and Driver for each iteration to ensure clean state
                app = Application(headless=True)
                # We need to manually set the scene to GameplayScene
                # MainMenuScene is usually the default, but we want GameplayScene for simulation
                scene = GameplayScene(app)
                app.scene_manager.push(scene)

                driver = GameDriver(app)
                driver.setup()

                # Spawn entities
                # We'll spawn them in a grid or randomly
                for _ in range(self.num_entities):
                    # Random position within bounds based on application size
                    width = app.width
                    height = app.height
                    x = (driver.frame_count * 1234 + _ * 5678) % (width - 50) + 25
                    y = (driver.frame_count * 9876 + _ * 4321) % (height - 50) + 25
                    driver.create_yukkuri("reimu", x, y)

                # Run simulation
                start_wall_time = time.perf_counter()
                driver.run_for(self.duration_seconds)
                end_wall_time = time.perf_counter()

                elapsed_wall_time = end_wall_time - start_wall_time

                # Calculate metrics
                # driver.frame_count tracks TOTAL frames since driver init.
                # But run_for increments it. We should track frames relative to this run if we didn't recreate driver.
                # Since we recreate driver, driver.frame_count is accurate for this run.
                # However, driver.setup() might advance frames? No, usually not.
                # But let's look at driver.frame_count difference just in case setup does something.
                # Actually, driver.frame_count starts at 0.

                frames = driver.frame_count
                if elapsed_wall_time > 0:
                    avg_fps = frames / elapsed_wall_time
                    sim_speed = driver.simulated_time / elapsed_wall_time
                else:
                    avg_fps = float('inf')
                    sim_speed = float('inf')

                fps_results.append(avg_fps)
                speed_ratio_results.append(sim_speed)

                print(f"Iteration {i+1}: {avg_fps:.2f} FPS, {sim_speed:.2f}x speed")

                driver.cleanup()

        avg_fps_mean = statistics.mean(fps_results)
        avg_speed_mean = statistics.mean(speed_ratio_results)

        return {
            "num_entities": self.num_entities,
            "duration_seconds": self.duration_seconds,
            "iterations": self.iterations,
            "fps_mean": avg_fps_mean,
            "fps_min": min(fps_results),
            "fps_max": max(fps_results),
            "speed_ratio_mean": avg_speed_mean
        }

def main():
    parser = argparse.ArgumentParser(description="Yukkuri Game Benchmark")
    parser.add_argument("--entities", type=int, default=100, help="Number of entities to spawn")
    parser.add_argument("--duration", type=float, default=10.0, help="Simulation duration in seconds")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations")

    args = parser.parse_args()

    runner = BenchmarkRunner(
        num_entities=args.entities,
        duration_seconds=args.duration,
        iterations=args.iterations
    )

    results = runner.run()

    print("\n--- Benchmark Results ---")
    print(f"Entities: {results['num_entities']}")
    print(f"Duration: {results['duration_seconds']}s")
    print(f"Average FPS: {results['fps_mean']:.2f}")
    print(f"Simulation Speed: {results['speed_ratio_mean']:.2f}x real-time")

if __name__ == "__main__":
    main()
