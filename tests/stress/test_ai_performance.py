
import pytest
import time
import random
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, MovementController, PhysicsBody
from yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, Needs, EmotionalState, Predator
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.game.systems.steering_system import SteeringSystem
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.services import GameService, TimeService
from yukkuri_game.engine.input_manager import InputManager

class TestAIPerformance:
    @pytest.fixture
    def world(self):
        world = World()
        # Mock services required by systems
        world.services.register(GameService, MagicMock())
        world.services.register(TimeService, MagicMock())
        world.services.register(InputManager, MagicMock())
        return world

    def test_stress_predator_prey(self, world):
        """
        Stress test with 50 Predators and 50 Prey.
        Benchmarks the update loop time.
        """
        # Systems
        perception_sys = PerceptionSystem()
        steering_sys = SteeringSystem()
        behavior_sys = BehaviorSystem(world_width=1000, world_height=1000)
        
        # Setup 100 entities
        for i in range(100):
            ent = world.create_entity()
            world.add_component(ent, Transform(x=random.randint(0, 1000), y=random.randint(0, 1000)))
            world.add_component(ent, MovementController())
            world.add_component(ent, PhysicsBody(body=MagicMock(), shape=MagicMock())) # Mock physics body
            world.add_component(ent, YukkuriStats(name=f"Yukkuri_{i}", type_id="reimu"))
            world.add_component(ent, AIState())
            world.add_component(ent, Needs())
            world.add_component(ent, EmotionalState())
            
            # 50 Predators, 50 Prey
            if i < 50:
                world.add_component(ent, Predator())
                # Give predators a hunger so they hunt
                world.get_component(ent, Needs).hunger = 0 # Very hungry
            else:
                # Prey (Reimu)
                pass

        # Warmup
        dt = 0.016
        perception_sys.update(world, dt)
        behavior_sys.update(world, dt)
        steering_sys.update(world, dt)

        # Benchmark
        start_time = time.time()
        frames = 100
        for _ in range(frames):
            perception_sys.update(world, dt)
            behavior_sys.update(world, dt)
            steering_sys.update(world, dt)
        
        duration = time.time() - start_time
        avg_frame_time = duration / frames
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 999.0
        
        print(f"\nStress Test Results (100 Entities):")
        print(f"Total Duration: {duration:.4f}s")
        print(f"Avg Frame Time: {avg_frame_time*1000:.2f}ms")
        print(f"Estimated FPS: {fps:.2f}")

        # Assert performance is reasonable (e.g., > 30 FPS logic update on test runner)
        # Note: Github Actions runners might be slow, so we set a relaxed threshold.
        # 33ms = 30 FPS.
        if avg_frame_time > 0.033:
            pytest.warns(UserWarning, match=f"AI System Performance Low: {fps:.2f} FPS")
        
        # We don't fail the test strictly on performance unless it's abysmal (< 10 FPS)
        assert fps > 10.0, f"Performance too low: {fps:.2f} FPS"
