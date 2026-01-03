import pymunk
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.visual_movement_system import VisualMovementSystem
from yukkuri_game.game.components import (
    PhysicsBody,
    MovementController,
    VisualTransform,
)
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.game.skill_constants import SkillId


def test_visual_movement_system_bobbing():
    world = World()
    system = VisualMovementSystem()
    world.add_system(system)

    # Create entity
    entity = world.create_entity()

    # Components
    space = pymunk.Space()
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    shape = pymunk.Circle(body, 10)
    space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController()
    visual = VisualTransform()

    world.add_component(entity, phys)
    world.add_component(entity, controller)
    world.add_component(entity, visual)

    # Mock velocity in controller (as if KinematicMovementSystem set it)
    controller.current_velocity = pymunk.Vec2d(100, 0)

    # Run update
    system.update(world, 0.1)

    # Check bobbing timer increased
    assert controller.visual_bob_timer > 0
    # Check vertical offset updated
    assert visual.vertical_offset >= 0


def test_visual_movement_system_xp():
    world = World()
    system = VisualMovementSystem()
    world.add_system(system)

    # Mock SkillService
    skill_service = MagicMock()
    # Correctly register with the type as key
    world.services.register(skill_service, SkillService)

    # Create entity
    entity = world.create_entity()

    # Components
    space = pymunk.Space()
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    shape = pymunk.Circle(body, 10)
    space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController()
    visual = VisualTransform()

    world.add_component(entity, phys)
    world.add_component(entity, controller)
    world.add_component(entity, visual)

    # Mock velocity
    controller.current_velocity = pymunk.Vec2d(100, 0)

    # Run update
    system.update(world, 0.1)

    # Verify XP added
    skill_service.add_xp.assert_called_once()
    args = skill_service.add_xp.call_args[0]
    assert args[0] == entity
    assert args[1] == SkillId.ATHLETICS
    assert args[2] > 0
