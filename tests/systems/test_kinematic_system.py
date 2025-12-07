
import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.kinematic_movement_system import KinematicMovementSystem
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import PhysicsBody, MovementController, Transform
from yukkuri_game.game.collision_constants import CollisionCategories

def test_kinematic_movement_slide():
    world = World()

    # Setup Physics System (needed for space)
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    kms = KinematicMovementSystem()
    world.add_system(kms)

    # Create Wall (Static)
    # Wall at x=100, vertical
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_body.position = (100, 0)
    wall_shape = pymunk.Segment(wall_body, (0, -100), (0, 100), 5) # Thickness 5
    wall_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.WALL)
    physics_system.space.add(wall_body, wall_shape)

    # Create Entity (Kinematic) at x=0
    entity = world.create_entity()
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = (0, 0)
    shape = pymunk.Circle(body, 10)
    shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI, mask=CollisionCategories.WALL)
    physics_system.space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController()
    trans = Transform(x=0, y=0)

    world.add_component(entity, phys)
    world.add_component(entity, controller)
    world.add_component(entity, trans)

    # Move diagonally towards wall
    # Velocity (100, 100). Should hit wall at x ~ 90 (100 - 5 thickness - 10 radius = 85 actually)
    # And slide upwards.
    controller.target_velocity = pymunk.Vec2d(100, 100)
    controller.acceleration = 10000 # Instant accel for test

    # Simulate for 1 second in steps
    dt = 1.0/60.0
    for _ in range(60):
        kms.update(world, dt)

    # Check Result
    # Should be close to the wall but not through it
    assert body.position.x < 100

    # Allow some slack in the position check due to floating point and segment query approximation
    assert 84.0 < body.position.x < 87.0

    # Y should have increased significantly (sliding up)
    assert body.position.y > 50.0

def test_kinematic_corner():
    world = World()
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)
    kms = KinematicMovementSystem()
    world.add_system(kms)

    # Corner: Vertical wall at x=100, Horizontal wall at y=100
    # Effective corner at (100, 100)

    # Wall 1 (Vertical)
    w1 = pymunk.Body(body_type=pymunk.Body.STATIC)
    w1.position = (100, 50)
    s1 = pymunk.Segment(w1, (0, -200), (0, 200), 5)
    s1.filter = pymunk.ShapeFilter(categories=CollisionCategories.WALL)
    physics_system.space.add(w1, s1)

    # Wall 2 (Horizontal)
    w2 = pymunk.Body(body_type=pymunk.Body.STATIC)
    w2.position = (50, 100)
    s2 = pymunk.Segment(w2, (-200, 0), (200, 0), 5)
    s2.filter = pymunk.ShapeFilter(categories=CollisionCategories.WALL)
    physics_system.space.add(w2, s2)

    # Entity
    entity = world.create_entity()
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = (50, 50)
    shape = pymunk.Circle(body, 10)
    shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI, mask=CollisionCategories.WALL)
    physics_system.space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController()
    trans = Transform(x=50, y=50)

    world.add_component(entity, phys)
    world.add_component(entity, controller)
    world.add_component(entity, trans)

    # Move diagonally into corner (100, 100)
    controller.target_velocity = pymunk.Vec2d(100, 100)
    controller.acceleration = 10000

    dt = 1.0/60.0
    for _ in range(120): # 2 seconds
        kms.update(world, dt)

    # Should be stopped near the corner
    # Wall 1 Surface x = 100 - 5 = 95. Center x = 85.
    # Wall 2 Surface y = 100 - 5 = 95. Center y = 85.

    print(f"Final Pos: {body.position}")
    assert 84.0 < body.position.x < 87.0
    assert 84.0 < body.position.y < 87.0
