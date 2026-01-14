"""
Benchmarking utility for performance regression testing.
"""

import time
import sys
import argparse
import json
import statistics
import platform
import gc
import csv
from typing import Any
import random
import logging

# Use Any for optional modules to avoid assignment errors with None
psutil: Any = None
try:
    import psutil
except ImportError:
    pass

np: Any = None
try:
    import numpy as np
except ImportError:
    pass

import cProfile

from ..testing.driver import GameDriver
from ..testing.environment import TestEnvironment
from ..engine.application import Application
from ..scenes.gameplay import GameplayScene

# Configure logging
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Runs performance benchmarks for the game.
    """

    def __init__(
        self,
        num_entities: int = 100,
        duration_seconds: float = 10.0,
        iterations: int = 3,
        warmup_seconds: float = 2.0,
        seed: int | None = None,
    ):
        """
        Initializes the BenchmarkRunner.

        Args:
            num_entities (int): Number of entities to spawn.
            duration_seconds (float): Game time duration to simulate per iteration.
            iterations (int): Number of iterations to run.
            warmup_seconds (float): Warmup time in seconds before measurement starts.
            seed (Optional[int]): Random seed for reproducibility.
        """
        self.num_entities = num_entities
        self.duration_seconds = duration_seconds
        self.iterations = iterations
        self.warmup_seconds = warmup_seconds
        self.seed = seed

    def _get_process_memory(self) -> float:
        """Returns current process memory usage in MB."""
        if psutil:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        return 0.0

    def _get_process_cpu(self) -> float:
        """Returns current process CPU usage percentage."""
        if psutil:
            process = psutil.Process()
            return process.cpu_percent(interval=None)
        return 0.0

    def _get_system_info(self) -> dict[str, str]:
        """Returns system information."""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        if psutil:
            info["cpu_count_physical"] = str(psutil.cpu_count(logical=False))
            info["cpu_count_logical"] = str(psutil.cpu_count(logical=True))
            try:
                info["cpu_freq_max"] = str(psutil.cpu_freq().max)
            except (AttributeError, FileNotFoundError):
                pass  # cpu_freq might not be available
        return info

    def run(
        self, profile: bool = False, profile_output: str = "benchmark_profile.stats"
    ) -> dict[str, Any]:
        """
        Runs the benchmark.

        Args:
            profile (bool): Whether to run with cProfile.
            profile_output (str): Filename to save profile stats.

        Returns:
            Dict[str, Any]: The benchmark results.
        """
        fps_results: list[float] = []
        speed_ratio_results: list[float] = []
        frame_time_stats: dict[str, list[float]] = {
            "p50": [],
            "p95": [],
            "p99": [],
            "jitter": [],
        }
        memory_usage: list[float] = []
        cpu_usage: list[float] = []

        # Store all raw frame times for CSV export [iteration][frame_index] -> ms
        all_raw_frame_times: list[list[float]] = []

        logger.info(
            f"Running benchmark with {self.num_entities} entities for {self.duration_seconds}s game time "
            f"(warmup: {self.warmup_seconds}s, {self.iterations} iterations)..."
        )

        if profile:
            profiler = cProfile.Profile()
            profiler.enable()

        successful_iterations = 0

        with TestEnvironment():
            for i in range(self.iterations):
                driver = None
                try:
                    # Force garbage collection to reduce variance
                    gc.collect()

                    # Set random seed for this iteration
                    current_seed = self.seed + i if self.seed is not None else None
                    if current_seed is not None:
                        random.seed(current_seed)
                        if np:
                            np.random.seed(current_seed)

                    # Initialize Application and Driver
                    app = Application(headless=True)
                    scene = GameplayScene(app)
                    app.scene_manager.push(scene)

                    driver = GameDriver(app)
                    driver.setup()

                    # Seed driver RNG as well if supported/needed
                    driver.seed_rng(current_seed if current_seed is not None else 42)

                    # Spawn entities
                    for j in range(self.num_entities):
                        width = app.width
                        height = app.height
                        # Use seeded random or deterministic placement
                        if current_seed is not None:
                            x = random.randint(25, width - 25)
                            y = random.randint(25, height - 25)
                        else:
                            x = (driver.frame_count * 1234 + j * 5678) % (
                                width - 50
                            ) + 25
                            y = (driver.frame_count * 9876 + j * 4321) % (
                                height - 50
                            ) + 25
                        driver.create_yukkuri("reimu", x, y)

                    # Warmup
                    if self.warmup_seconds > 0:
                        driver.run_for(self.warmup_seconds)

                    # Reset CPU measurement
                    if psutil:
                        psutil.Process().cpu_percent(interval=None)

                    # Run measured simulation
                    target_sim_time = driver.simulated_time + self.duration_seconds
                    frame_times = []

                    start_wall_time = time.perf_counter()

                    while driver.simulated_time < target_sim_time:
                        frame_start = time.perf_counter()
                        driver._tick()
                        frame_end = time.perf_counter()
                        frame_times.append(frame_end - frame_start)

                    end_wall_time = time.perf_counter()
                    elapsed_wall_time = end_wall_time - start_wall_time

                    # Collect metrics
                    frames = len(frame_times)
                    if elapsed_wall_time > 0:
                        avg_fps = frames / elapsed_wall_time
                        sim_speed = (
                            self.duration_seconds
                        ) / elapsed_wall_time  # Approximate
                    else:
                        avg_fps = float("inf")
                        sim_speed = float("inf")

                    fps_results.append(avg_fps)
                    speed_ratio_results.append(sim_speed)

                    if frame_times:
                        frame_times_ms = [t * 1000 for t in frame_times]
                        all_raw_frame_times.append(frame_times_ms)

                        frame_time_stats["p50"].append(
                            statistics.median(frame_times_ms)
                        )

                        if np:
                            frame_time_stats["p95"].append(
                                np.percentile(frame_times_ms, 95)
                            )
                            frame_time_stats["p99"].append(
                                np.percentile(frame_times_ms, 99)
                            )
                        else:
                            frame_time_stats["p95"].append(
                                statistics.quantiles(frame_times_ms, n=20)[18]
                                if len(frame_times_ms) >= 20
                                else max(frame_times_ms)
                            )
                            frame_time_stats["p99"].append(
                                statistics.quantiles(frame_times_ms, n=100)[98]
                                if len(frame_times_ms) >= 100
                                else max(frame_times_ms)
                            )

                        if len(frame_times_ms) > 1:
                            frame_time_stats["jitter"].append(
                                statistics.stdev(frame_times_ms)
                            )
                        else:
                            frame_time_stats["jitter"].append(0.0)

                    if psutil:
                        memory_usage.append(self._get_process_memory())
                        cpu_usage.append(self._get_process_cpu())

                    logger.info(
                        f"Iteration {i + 1}: {avg_fps:.2f} FPS, {sim_speed:.2f}x speed"
                    )
                    successful_iterations += 1

                except Exception as e:
                    logger.error(f"Iteration {i + 1} failed: {e}", exc_info=True)

                finally:
                    if driver:
                        try:
                            driver.cleanup()
                        except Exception as e:
                            logger.error(
                                f"Failed to cleanup driver in iteration {i + 1}: {e}"
                            )

        if profile:
            profiler.disable()
            logger.info(f"Saving profile stats to {profile_output}")
            profiler.dump_stats(profile_output)

        if successful_iterations == 0:
            logger.error("All iterations failed.")
            return {}

        results: dict[str, Any] = {
            "config": {
                "num_entities": self.num_entities,
                "duration_seconds": self.duration_seconds,
                "iterations": self.iterations,
                "warmup_seconds": self.warmup_seconds,
                "seed": self.seed,
            },
            "system_info": self._get_system_info(),
            "results": {
                "fps": {
                    "mean": statistics.mean(fps_results) if fps_results else 0.0,
                    "min": min(fps_results) if fps_results else 0.0,
                    "max": max(fps_results) if fps_results else 0.0,
                    "stdev": statistics.stdev(fps_results)
                    if len(fps_results) > 1
                    else 0.0,
                },
                "speed_ratio_mean": statistics.mean(speed_ratio_results)
                if speed_ratio_results
                else 0.0,
                "frame_time_ms": {
                    "p50_mean": statistics.mean(frame_time_stats["p50"])
                    if frame_time_stats["p50"]
                    else 0.0,
                    "p95_mean": statistics.mean(frame_time_stats["p95"])
                    if frame_time_stats["p95"]
                    else 0.0,
                    "p99_mean": statistics.mean(frame_time_stats["p99"])
                    if frame_time_stats["p99"]
                    else 0.0,
                    "jitter_mean": statistics.mean(frame_time_stats["jitter"])
                    if frame_time_stats["jitter"]
                    else 0.0,
                },
            },
            "raw_frame_times": all_raw_frame_times,
        }

        if psutil:
            results["results"]["system"] = {
                "memory_mb_mean": statistics.mean(memory_usage)
                if memory_usage
                else 0.0,
                "cpu_percent_mean": statistics.mean(cpu_usage) if cpu_usage else 0.0,
            }

        return results


def compare_results(current: dict[str, Any], baseline: dict[str, Any]) -> None:
    """
    Compares current results with baseline and prints difference.
    """
    print("\n--- Baseline Comparison ---")

    metrics = [
        ("FPS (Mean)", ["results", "fps", "mean"]),
        ("Frame Time p99 (Mean)", ["results", "frame_time_ms", "p99_mean"]),
        ("Simulation Speed", ["results", "speed_ratio_mean"]),
    ]

    for label, path in metrics:
        curr_val: Any = current
        base_val: Any = baseline
        try:
            for key in path:
                curr_val = curr_val[key]
                base_val = base_val[key]

            # Ensure values are numbers for subtraction
            if isinstance(curr_val, (int, float)) and isinstance(
                base_val, (int, float)
            ):
                diff = curr_val - base_val
                pct = (diff / base_val * 100) if base_val != 0 else 0.0
            else:
                continue

            # For frame time, lower is better. For FPS/Speed, higher is better.

            sign = "+" if pct > 0 else ""
            print(f"{label}: {base_val:.2f} -> {curr_val:.2f} ({sign}{pct:.2f}%)")

        except KeyError:
            print(f"{label}: Could not find metric in one of the results.")


def export_csv(results: dict[str, Any], filepath: str):
    """
    Exports raw frame times to CSV.
    Format: iteration, frame_index, frame_time_ms
    """
    try:
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["iteration", "frame_index", "frame_time_ms"])

            raw_data = results.get("raw_frame_times", [])
            for i, iteration_data in enumerate(raw_data):
                for j, frame_time in enumerate(iteration_data):
                    writer.writerow([i + 1, j + 1, frame_time])

        logger.info(f"Raw data exported to {filepath}")
    except OSError as e:
        logger.error(f"Failed to write CSV: {e}")


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Yukkuri Game Benchmark")
    parser.add_argument(
        "--entities", type=int, default=100, help="Number of entities to spawn"
    )
    parser.add_argument(
        "--duration", type=float, default=10.0, help="Simulation duration in seconds"
    )
    parser.add_argument(
        "--iterations", type=int, default=3, help="Number of iterations"
    )
    parser.add_argument(
        "--warmup", type=float, default=2.0, help="Warmup duration in seconds"
    )
    parser.add_argument("--json", type=str, help="Output results to JSON file")
    parser.add_argument("--csv", type=str, help="Output raw frame times to CSV file")
    parser.add_argument(
        "--baseline", type=str, help="Baseline JSON file to compare against"
    )
    parser.add_argument("--profile", action="store_true", help="Run with cProfile")
    parser.add_argument(
        "--profile-output",
        type=str,
        default="benchmark_profile.stats",
        help="Profile output file",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    runner = BenchmarkRunner(
        num_entities=args.entities,
        duration_seconds=args.duration,
        iterations=args.iterations,
        warmup_seconds=args.warmup,
        seed=args.seed,
    )

    results = runner.run(profile=args.profile, profile_output=args.profile_output)

    if not results:
        print("Benchmark failed.")
        sys.exit(1)

    print("\n--- Benchmark Results ---")
    print(f"Entities: {results['config']['num_entities']}")
    print(f"Duration: {results['config']['duration_seconds']}s")
    print(f"FPS (Mean): {results['results']['fps']['mean']:.2f}")
    print(
        f"Frame Time p99 (Mean): {results['results']['frame_time_ms']['p99_mean']:.2f} ms"
    )
    print(f"Simulation Speed: {results['results']['speed_ratio_mean']:.2f}x real-time")

    if "system" in results["results"]:
        print(f"Memory Usage: {results['results']['system']['memory_mb_mean']:.2f} MB")
        print(f"CPU Usage: {results['results']['system']['cpu_percent_mean']:.2f}%")

    if args.baseline:
        try:
            with open(args.baseline) as f:
                baseline_results = json.load(f)
            compare_results(results, baseline_results)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load baseline: {e}")

    if args.json:
        # Don't save raw_frame_times in the main summary JSON if it's huge,
        # but here we include it for completeness unless we want to separate it.
        # For now, I'll include it.
        try:
            with open(args.json, "w") as f:
                json.dump(results, f, indent=4)
            print(f"Results saved to {args.json}")
        except OSError as e:
            logger.error(f"Failed to save JSON results: {e}")

    if args.csv:
        export_csv(results, args.csv)


if __name__ == "__main__":
    main()
