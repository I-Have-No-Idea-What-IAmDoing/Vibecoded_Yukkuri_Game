import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.types import EntityID
from yukkuri_game.game.services import TimeService
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.game.systems.kinematic_movement_system import KinematicMovementSystem
from yukkuri_game.game.yukkuri_components import AIState, Blackboard, YukkuriStats, TargetInfo
from yukkuri_game.game.components import Transform, PhysicsBody, MovementController

class TestAgilityIntegration:
    
    def test_perception_reaction_buffering(self):
        """Test that perception system buffers reaction based on lag."""
        world = World()
        system = PerceptionSystem()
        
        # Setup TimeService and EventBus mocks
        time_service = MagicMock()
        time_service.time_elapsed = 0.0
        
        event_bus = MagicMock()
        
        def service_side_effect(service_type):
            if "TimeService" in str(service_type):
                return time_service
            if "EventBus" in str(service_type):
                return event_bus
            return None
            
        world.services.try_get = MagicMock(side_effect=service_side_effect)
        entity = world.create_entity()
        world.add_component(entity, AIState())
        world.add_component(entity, Blackboard())
        world.add_component(entity, Transform(x=0, y=0))
        
        # High Agility = Low Delay (0.5 / 2.0 = 0.25s)
        world.add_component(entity, YukkuriStats(name="Test", type_id="test", agility=2.0))
        
        # Setup target
        target = world.create_entity()
        world.add_component(target, Transform(x=10, y=0)) # Nearby
        world.add_component(target, YukkuriStats(name="Target", type_id="enemy", agility=1.0)) # Enemy relation logic depends on more input, so let's mock _resolve_relation
        
        # Mock _resolve_relation to return Enemy
        system._resolve_relation = MagicMock(return_value="Enemy")
        
        ai_state = world.get_component(entity, AIState)
        ai_state.visible_entities = {target}
        blackboard = world.get_component(entity, Blackboard)
        
        # --- Frame 1: Top of detection (Time 0.0) ---
        time_service.time_elapsed = 0.0
        system.update(world, 0.1)
        
        assert blackboard.nearby_enemies == 0, "Should buffer reaction initially"
        assert target in blackboard.visible_targets
        assert blackboard.visible_targets[target].detected_at == 0.0
        
        # --- Frame 2: Still buffering (Time 0.2 < 0.25) ---
        time_service.time_elapsed = 0.2
        system.update(world, 0.1)
        assert blackboard.nearby_enemies == 0, "Should still be buffering"
        assert blackboard.visible_targets[target].detected_at == 0.0 # Should persist
        
        # --- Frame 3: Reaction Triggered (Time 0.31 > 0.25 and > 0.2 + 0.1) ---
        time_service.time_elapsed = 0.31
        system.update(world, 0.1)
        
        assert blackboard.nearby_enemies == 1, "Should react now"
        
    def test_kinematic_agility_scaling(self):
        """Smoke test to ensure KinematicMovementSystem accepts agility."""
        world = World()
        system = KinematicMovementSystem()
        
        entity = world.create_entity()
        # PhysicsBody needs body and shape
        import pymunk
        mock_body = MagicMock()
        mock_body.body_type = pymunk.Body.KINEMATIC
        mock_shape = MagicMock()
        world.add_component(entity, PhysicsBody(body=mock_body, shape=mock_shape))
        world.add_component(entity, MovementController(acceleration=10.0, target_velocity=pymunk.Vec2d(10, 0)))
        world.add_component(entity, Transform(x=0.0, y=0.0))
        world.add_component(entity, YukkuriStats(name="Test", type_id="test", agility=2.0))
        
        # Just running update to check for crashes and correct call signature
        # We can't easily verify the internal acceleration usage without spying on move_and_slide
        # But we can verify it runs.
        
        # Mock move_and_slide to verify it receives agility
        system.move_and_slide = MagicMock(return_value=1.0)
        
        # Need to init system
        world.services.try_get = MagicMock()
        system.update(world, 0.1)
        system.space = MagicMock() # Mock space
        
        # Fake FixedUpdate
        from yukkuri_game.engine.events import PhysicsFixedUpdateEvent
        system.on_fixed_update(PhysicsFixedUpdateEvent(dt=0.1))
        
        # Verify allow call with agility
        # The system calls move_and_slide(phys, controller, trans, dt, agility)
        system.move_and_slide.assert_called()
        args, kwargs = system.move_and_slide.call_args
        # args: phys, controller, trans, dt, agility
        assert len(args) == 5
        assert args[4] == 2.0 # Agility passed correctly check
