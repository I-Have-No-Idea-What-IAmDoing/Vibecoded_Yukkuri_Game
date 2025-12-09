import os
import json
import pytest
from unittest.mock import MagicMock, patch
from src.yukkuri_game.benchmarks.benchmark import BenchmarkRunner

class TestBenchmarkRunner:
    @patch('src.yukkuri_game.benchmarks.benchmark.Application')
    @patch('src.yukkuri_game.benchmarks.benchmark.GameplayScene')
    @patch('src.yukkuri_game.benchmarks.benchmark.GameDriver')
    @patch('src.yukkuri_game.benchmarks.benchmark.TestEnvironment')
    def test_run_benchmark(self, mock_env, mock_driver_cls, mock_scene, mock_app):
        # Setup mocks
        mock_driver = mock_driver_cls.return_value
        mock_driver.simulated_time = 0.0

        # Mock _tick to advance simulated time so the loop terminates
        def side_effect_tick():
            mock_driver.simulated_time += 0.1

        mock_driver._tick.side_effect = side_effect_tick

        # Configure app mock
        mock_app.return_value.width = 800
        mock_app.return_value.height = 600

        # Initialize runner
        runner = BenchmarkRunner(
            num_entities=10,
            duration_seconds=0.5,
            iterations=1,
            warmup_seconds=0.1,
            seed=42
        )

        # Run benchmark
        results = runner.run()

        # Assertions
        assert results['config']['num_entities'] == 10
        assert results['config']['duration_seconds'] == 0.5
        assert results['config']['iterations'] == 1
        assert results['config']['warmup_seconds'] == 0.1
        assert results['config']['seed'] == 42

        assert 'fps' in results['results']
        assert 'frame_time_ms' in results['results']

        # Verify driver interactions
        assert mock_driver.setup.called
        assert mock_driver.create_yukkuri.call_count == 10
        assert mock_driver.run_for.called # Warmup
        assert mock_driver._tick.called # Measurement loop
        assert mock_driver.cleanup.called

    def test_json_output(self, tmp_path):
        import argparse
        from src.yukkuri_game.benchmarks.benchmark import main

        # Create a dummy json file path
        output_file = tmp_path / "test_output.json"

        # Mock sys.argv
        with patch('sys.argv', ['benchmark.py', '--iterations', '1', '--duration', '0.1', '--warmup', '0.0', '--entities', '5', '--json', str(output_file)]):
            # We need to mock the runner to avoid actually running the game which might need display or take time
            with patch('src.yukkuri_game.benchmarks.benchmark.BenchmarkRunner') as MockRunner:
                mock_instance = MockRunner.return_value
                mock_instance.run.return_value = {
                    "config": {"num_entities": 5, "duration_seconds": 0.1, "iterations": 1, "warmup_seconds": 0.0, "seed": 42},
                    "results": {
                        "fps": {"mean": 60.0, "min": 60.0, "max": 60.0},
                        "speed_ratio_mean": 1.0,
                        "frame_time_ms": {"p99_mean": 16.0},
                        "system": {"memory_mb_mean": 100.0, "cpu_percent_mean": 10.0}
                    }
                }

                main()

                # Check if file was created
                assert output_file.exists()
                with open(output_file) as f:
                    data = json.load(f)
                    assert data['config']['num_entities'] == 5
