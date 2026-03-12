
import unittest
from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
import logging

# Disable logs for this test to avoid noise
logging.getLogger().setLevel(logging.ERROR)

class TestDeterminism(unittest.TestCase):
    def run_simulation(self, seed_val: int, frames: int):
        app = Application(headless=True, deterministic=True)
        driver = GameDriver(app, fixed_dt=1.0/60.0)
        
        driver.setup()

        # Explicitly seed (Application handles it if deterministic=True, but driver also sets it)
        # Driver calls seed_rng() in setup() with default 42.
        # We need to override it AFTER setup.
        driver.seed_rng(seed_val)
        
        # Spawn some entities to generate activity
        driver.create_yukkuri("reimu", 100, 100)
        driver.create_yukkuri("marisa", 200, 200)
        
        # Run
        for _ in range(frames):
            driver._tick()
            
        state = driver.dump_state()
        driver.cleanup()
        return state

    def test_determinism_match(self):
        """Run simulation twice with same seed and compare states."""
        seed = 12345
        frames = 30
        
        state_1 = self.run_simulation(seed, frames)
        state_2 = self.run_simulation(seed, frames)
        
        # Debugging output if mismatch
        if state_1 != state_2:
            import difflib
            diff = difflib.unified_diff(
                state_1.splitlines(), 
                state_2.splitlines(), 
                fromfile='Run1', 
                tofile='Run2', 
                lineterm=''
            )
            print("\n".join(diff))
            
        self.assertEqual(state_1, state_2, "Game runs with same seed must be identical.")

    def test_determinism_diverge(self):
        """Run simulation twice with DIFFERENT seeds and expect difference."""
        frames = 30
        
        state_1 = self.run_simulation(11111, frames)
        state_2 = self.run_simulation(99999, frames)
        
        self.assertNotEqual(state_1, state_2, "Game runs with different seeds must diverge.")

if __name__ == "__main__":
    unittest.main()
