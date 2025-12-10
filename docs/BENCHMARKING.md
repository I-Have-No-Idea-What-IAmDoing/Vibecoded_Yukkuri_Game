# Benchmarking Package

The Benchmarking package (`yukkuri_game.benchmarks`) provides tools to measure and analyze the performance of the Yukkuri Game. It allows developers to run standardized scenarios, collect metrics like FPS and memory usage, and compare results against baselines to detect regressions.

## Prerequisites

The package uses standard Python libraries. For enhanced metrics (memory/CPU usage) and statistical analysis, the following optional dependencies are recommended:

*   `psutil`: For memory and CPU usage tracking.
*   `numpy`: For more accurate percentile calculations.

## Command Line Usage

You can run the benchmark directly from the command line:

```bash
python -m yukkuri_game.benchmarks.benchmark [OPTIONS]
```

### Arguments

| Argument | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--entities` | `int` | `100` | Number of entities to spawn in the simulation. |
| `--duration` | `float` | `10.0` | Simulation duration in seconds (game time). |
| `--iterations` | `int` | `3` | Number of times to run the benchmark. |
| `--warmup` | `float` | `2.0` | Warmup duration in seconds before measurement starts. |
| `--seed` | `int` | `42` | Random seed for reproducibility. |
| `--json` | `str` | `None` | Path to save the results in JSON format. |
| `--csv` | `str` | `None` | Path to save raw frame times in CSV format. |
| `--baseline` | `str` | `None` | Path to a previous JSON result file to compare against. |
| `--profile` | `flag` | `False` | Enable cProfile for detailed performance analysis. |
| `--profile-output`| `str` | `benchmark_profile.stats` | Output file for cProfile stats. |

### Examples

**Basic run:**
```bash
python -m yukkuri_game.benchmarks.benchmark --entities 200 --duration 20
```

**Save results for future comparison:**
```bash
python -m yukkuri_game.benchmarks.benchmark --json baseline.json
```

**Compare against a baseline:**
```bash
python -m yukkuri_game.benchmarks.benchmark --baseline baseline.json
```

**Export raw data for analysis:**
```bash
python -m yukkuri_game.benchmarks.benchmark --csv frame_times.csv
```

## Programmatic Usage

You can also use the `BenchmarkRunner` class within your Python scripts.

```python
from yukkuri_game.benchmarks.benchmark import BenchmarkRunner

# Initialize the runner
runner = BenchmarkRunner(
    num_entities=150,
    duration_seconds=5.0,
    iterations=5,
    warmup_seconds=1.0,
    seed=123
)

# Run the benchmark
results = runner.run()

# Access results
print(f"Mean FPS: {results['results']['fps']['mean']}")
```

## Output Formats

### JSON Output

The JSON output contains configuration details, system information, aggregate results, and raw frame times.

```json
{
    "config": {
        "num_entities": 100,
        "duration_seconds": 10.0,
        "iterations": 3,
        ...
    },
    "system_info": {
        "system": "Linux",
        "processor": "x86_64",
        ...
    },
    "results": {
        "fps": {
            "mean": 60.5,
            "min": 58.2,
            "max": 62.1,
            "stdev": 1.5
        },
        "speed_ratio_mean": 1.0,
        "frame_time_ms": {
            "p50_mean": 16.5,
            "p95_mean": 18.2,
            "p99_mean": 20.1,
            "jitter_mean": 0.5
        },
        "system": {
            "memory_mb_mean": 150.5,
            "cpu_percent_mean": 15.2
        }
    },
    "raw_frame_times": [
        [16.2, 16.5, ...], // Iteration 1
        [16.1, 16.4, ...]  // Iteration 2
    ]
}
```

### CSV Output

The CSV output is useful for detailed plotting. It contains three columns:

*   `iteration`: The iteration number (1-based).
*   `frame_index`: The frame number within that iteration (1-based).
*   `frame_time_ms`: The time taken to render that frame in milliseconds.

## Profiling

To identify bottlenecks, use the `--profile` flag. This uses Python's built-in `cProfile` module.

```bash
python -m yukkuri_game.benchmarks.benchmark --profile --profile-output my_profile.stats
```

You can visualize the output using tools like `snakeviz` or `tuna`.

```bash
snakeviz my_profile.stats
```
