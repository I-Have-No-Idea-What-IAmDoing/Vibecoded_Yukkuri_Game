"""
Lighting subsystem benchmark.
"""

import time
import argparse
import json
import statistics
import random
import pygame
import csv
from typing import Dict, Any
import logging

from ..game.renderer.pygame_backend import PygameBackend
from ..game.renderer.commands import LightCommand, OccluderCommand


# Reuse utils from the main benchmark module

# Configure logging
logger = logging.getLogger(__name__)


class LightingBenchmarkRunner:
    """
    Runs performance benchmarks for the lighting subsystem.
    """

    def __init__(
        self,
        num_lights: int = 20,
        num_occluders: int = 50,
        iterations: int = 20,
        seed: int = 42,
    ):
        self.num_lights = num_lights
        self.num_occluders = num_occluders
        self.iterations = iterations
        self.seed = seed

    def run(self) -> Dict[str, Any]:
        """
        Runs the benchmark.
        """
        logger.info(
            f"Running lighting benchmark: Lights={self.num_lights}, Occluders={self.num_occluders}, "
            f"Iterations={self.iterations}"
        )

        pygame.init()
        # Dummy screen
        screen = pygame.Surface((1920, 1080))
        backend = PygameBackend(screen)

        random.seed(self.seed)

        # Create Occluders
        occluder_vertices_list = []
        backend.begin_frame()

        for i in range(self.num_occluders):
            x = random.randint(0, 1900)
            y = random.randint(0, 1060)
            w = random.randint(20, 50)
            h = random.randint(20, 50)
            verts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]

            backend.draw_occluder(
                OccluderCommand(
                    layer=0, z_index=0, entity_id=i, vertices=verts, static=True
                )
            )

            # Keep track for direct caster comparison
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            aabb = (min(xs), max(xs), min(ys), max(ys))
            occluder_vertices_list.append((aabb, verts))

        # Create Lights
        lights = []
        for i in range(self.num_lights):
            l = LightCommand(
                layer=1,
                z_index=0,
                entity_id=i + 1000,
                position=(random.randint(0, 1920), random.randint(0, 1080)),
                radius=300,
                color=(255, 200, 150, 255),
                intensity=1.0,
            )
            lights.append(l)
            backend.draw_light(l)

        # 1. Uncached (Removed as ShadowCaster is deprecated)
        uncached_times = [0.0] * self.iterations

        # 2. Cached (Backend)
        # Populate Cache
        backend.end_frame()

        cached_times = []

        start_time = time.perf_counter()
        for _ in range(self.iterations):
            frame_start = time.perf_counter()

            backend.begin_frame()
            # Re-submit occluders
            for i in range(self.num_occluders):
                (aabb, verts) = occluder_vertices_list[i]
                backend.draw_occluder(
                    OccluderCommand(
                        layer=0, z_index=0, entity_id=i, vertices=verts, static=True
                    )
                )

            for l in lights:
                backend.draw_light(l)

            backend.end_frame()

            frame_end = time.perf_counter()
            cached_times.append((frame_end - frame_start) * 1000)

        results = {
            "config": {
                "num_lights": self.num_lights,
                "num_occluders": self.num_occluders,
                "iterations": self.iterations,
                "seed": self.seed,
            },
            "results": {
                "uncached_ms": {
                    "mean": statistics.mean(uncached_times),
                    "min": min(uncached_times),
                    "max": max(uncached_times),
                },
                "cached_ms": {
                    "mean": statistics.mean(cached_times),
                    "min": min(cached_times),
                    "max": max(cached_times),
                },
                "speedup": statistics.mean(uncached_times)
                / statistics.mean(cached_times)
                if statistics.mean(cached_times) > 0
                else 0,
            },
            "raw_times": {"uncached": uncached_times, "cached": cached_times},
        }

        return results


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Lighting Subsystem Benchmark")
    parser.add_argument("--lights", type=int, default=20, help="Number of lights")
    parser.add_argument("--occluders", type=int, default=50, help="Number of occluders")
    parser.add_argument(
        "--iterations", type=int, default=20, help="Number of iterations"
    )
    parser.add_argument("--json", type=str, help="Output results to JSON file")
    parser.add_argument("--csv", type=str, help="Output raw times to CSV file")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    runner = LightingBenchmarkRunner(
        num_lights=args.lights,
        num_occluders=args.occluders,
        iterations=args.iterations,
        seed=args.seed,
    )

    results = runner.run()

    print("\n--- Benchmark Results ---")
    print(
        f"Lights: {results['config']['num_lights']}, Occluders: {results['config']['num_occluders']}"
    )
    print(f"Uncached Time (Mean): {results['results']['uncached_ms']['mean']:.2f} ms")
    print(f"Cached Time (Mean): {results['results']['cached_ms']['mean']:.2f} ms")
    print(f"Speedup: {results['results']['speedup']:.2f}x")

    if args.json:
        try:
            with open(args.json, "w") as f:
                json.dump(results, f, indent=4)
            print(f"Results saved to {args.json}")
        except IOError as e:
            logger.error(f"Failed to save JSON results: {e}")

    if args.csv:
        # Custom CSV export for this format
        try:
            with open(args.csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["iteration", "uncached_ms", "cached_ms"])
                for i in range(len(results["raw_times"]["uncached"])):
                    writer.writerow(
                        [
                            i + 1,
                            results["raw_times"]["uncached"][i],
                            results["raw_times"]["cached"][i],
                        ]
                    )
            print(f"Raw data exported to {args.csv}")
        except IOError as e:
            logger.error(f"Failed to write CSV: {e}")


if __name__ == "__main__":
    main()
