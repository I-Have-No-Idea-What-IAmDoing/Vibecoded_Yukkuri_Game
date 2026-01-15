import unittest
import os
import tempfile
import logging
from unittest.mock import patch
from yukkuri_game.benchmarks.benchmark import (
    BenchmarkRunner,
    compare_results,
    export_csv,
)


class TestBenchmark(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for output files
        self.test_dir = tempfile.TemporaryDirectory()
        # Configure logging to capture output if needed, or suppress it
        logging.getLogger("yukkuri_game.benchmarks.benchmark").setLevel(
            logging.CRITICAL
        )

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("yukkuri_game.benchmarks.benchmark.Application")
    @patch("yukkuri_game.benchmarks.benchmark.GameplayScene")
    @patch("yukkuri_game.benchmarks.benchmark.GameDriver")
    def test_benchmark_run(self, mock_driver_cls, mock_scene_cls, mock_app_cls):
        # Setup mocks
        mock_driver = mock_driver_cls.return_value
        mock_driver.simulated_time = 0.0

        mock_app = mock_app_cls.return_value
        mock_app.width = 800
        mock_app.height = 600

        # Determine how many steps needed to exceed duration
        # If duration is 0.1s, and we increment by 0.05s per tick
        def tick_side_effect():
            mock_driver.simulated_time += 0.05

        mock_driver._tick.side_effect = tick_side_effect

        runner = BenchmarkRunner(
            num_entities=1,
            duration_seconds=0.1,
            iterations=2,
            warmup_seconds=0.0,
            seed=42,
        )

        results = runner.run()

        self.assertIn("results", results)
        self.assertIn("fps", results["results"])
        self.assertIn("frame_time_ms", results["results"])
        self.assertIn("system_info", results)
        self.assertEqual(results["config"]["iterations"], 2)

        # Verify mocked calls
        self.assertEqual(mock_driver_cls.call_count, 2)
        self.assertEqual(mock_driver.setup.call_count, 2)
        self.assertEqual(mock_driver.cleanup.call_count, 2)

    def test_export_csv(self) -> None:
        results = {"raw_frame_times": [[16.6, 16.7, 16.6], [16.5, 16.6, 16.8]]}
        filepath = os.path.join(self.test_dir.name, "test.csv")
        export_csv(results, filepath)

        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r") as f:
            lines = f.readlines()
            # Header + 6 data rows
            self.assertEqual(len(lines), 7)
            self.assertEqual(lines[0].strip(), "iteration,frame_index,frame_time_ms")
            self.assertEqual(lines[1].strip(), "1,1,16.6")

    def test_compare_results(self) -> None:
        # This function prints to stdout, we won't capture it here but just ensure it runs without error
        current = {
            "results": {
                "fps": {"mean": 60.0},
                "frame_time_ms": {"p99_mean": 16.0},
                "speed_ratio_mean": 1.0,
            }
        }
        baseline = {
            "results": {
                "fps": {"mean": 50.0},
                "frame_time_ms": {"p99_mean": 20.0},
                "speed_ratio_mean": 0.8,
            }
        }

        try:
            compare_results(current, baseline)
        except Exception as e:
            self.fail(f"compare_results raised Exception: {e}")


if __name__ == "__main__":
    unittest.main()
