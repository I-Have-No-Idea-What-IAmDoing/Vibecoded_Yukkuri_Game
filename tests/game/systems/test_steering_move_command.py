import pytest
from unittest.mock import MagicMock
import pymunk
from yukkuri_game.game.systems.steering_system import SteeringSystem
from yukkuri_game.game.components import (
    MoveCommand,
    SteeringComponent,
)
from yukkuri_game.engine.components import (
    Transform,
    MovementController,
    PhysicsBody,
)
from yukkuri_game.game.components import AIState
from yukkuri_game.engine.ecs import World


class TestSteeringMoveCommand:
    @pytest.fixture
    def world(self):
        w = MagicMock(spec=World)
        w.services = MagicMock()
        w.try_get_component.return_value = None
        return w

    @pytest.fixture
    def system(self):
        return SteeringSystem()

    def test_move_command_processing(self, world, system):
        """Test that MoveCommand is consumed and sets velocity."""
        entity_id = 1

        # Setup Components
        trans = Transform(x=0, y=0)
        movement = MovementController()
        steering = SteeringComponent(max_speed=100.0, arrival_radius=10.0)
        phys = MagicMock(spec=PhysicsBody)
        phys.body = MagicMock()

        # Create MoveCommand targeting (100, 0)
        move_cmd = MoveCommand(target_pos=pymunk.Vec2d(100, 0))

        # Mock world.get_components_tuple for MoveCommand phase
        world.get_components_tuple.side_effect = [
            [
                (entity_id, (trans, movement, steering, phys, move_cmd))
            ],  # Phase A: MoveCommand
            [],  # Phase B: Path-based
        ]

        # Mock PhysicsSystem for space (even if None)
        world.services.try_get.return_value = None

        system.update(world, dt=0.1)

        # Verify velocity is set towards target
        assert movement.target_velocity.x > 0
        assert movement.target_velocity.y == 0
        # Expected speed is max_speed since far away
        assert movement.target_velocity.length == pytest.approx(100.0)

    def test_move_command_arrival(self, world, system):
        """Test that MoveCommand is removed upon arrival."""
        entity_id = 1

        trans = Transform(x=95, y=0)  # 5 units away from 100
        movement = MovementController()
        steering = SteeringComponent(max_speed=100.0, arrival_radius=10.0)  # Radius 10
        phys = MagicMock()

        move_cmd = MoveCommand(target_pos=pymunk.Vec2d(100, 0))

        world.get_components_tuple.side_effect = [
            [(entity_id, (trans, movement, steering, phys, move_cmd))],
            [],
        ]
        world.services.try_get.return_value = None

        system.update(world, dt=0.1)

        # Verify MoveCommand is removed
        world.remove_component.assert_called_once_with(entity_id, MoveCommand)
        # Verify velocity zeroed (or near zero depending on logic, here explicitly zeroed in code)
        assert movement.target_velocity == pymunk.Vec2d(0, 0)

    def test_move_command_override_path(self, world, system):
        """Test that MoveCommand takes precedence over AIState path."""
        entity_id = 1

        trans = Transform(x=0, y=0)
        movement = MovementController()
        steering = SteeringComponent(max_speed=100.0)
        phys = MagicMock()
        ai_state = AIState(path=[(0, 100)])  # Path points UP
        move_cmd = MoveCommand(target_pos=pymunk.Vec2d(100, 0))  # Command points RIGHT

        # In Phase A, we return the entity with MoveCommand
        # In Phase B, we return the entity with AIState logic
        # But the loop in Phase B should skip checks if MoveCommand exists.
        # Wait, Phase B iterates components tuple (Transform, ... AIState ...). It doesn't know about MoveCommand unless we check world.has_component.

        world.get_components_tuple.side_effect = [
            [(entity_id, (trans, movement, steering, phys, move_cmd))],  # Phase A
            [(entity_id, (trans, movement, steering, ai_state, phys))],  # Phase B
        ]
        world.services.try_get.return_value = None
        world.has_component.return_value = (
            True  # Simulate entity has MoveCommand during Phase B check
        )

        system.update(world, dt=0.1)

        # Should move RIGHT (MoveCommand), not UP (Path)
        assert movement.target_velocity.x > 0
        assert movement.target_velocity.y == 0
