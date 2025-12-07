
import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.visibility_system import VisibilitySystem
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import PhysicsBody, Transform, Vision, Mount
from yukkuri_game.game.yukkuri_components import AIState
from yukkuri_game.game.collision_constants import CollisionCategories

def test_visibility_occlusion():
    world = World()

    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer (Yukkuri) at (0, 0)
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(obs_body, obs_shape)

    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0))
    world.add_component(obs, Vision(range=200, fov=360))
    world.add_component(obs, AIState())

    # Target (Yukkuri) at (100, 0) - Visible
    target1 = world.create_entity()
    t1_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t1_body.position = (100, 0)
    t1_shape = pymunk.Circle(t1_body, 10)
    t1_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(t1_body, t1_shape)

    world.add_component(target1, PhysicsBody(body=t1_body, shape=t1_shape))
    world.add_component(target1, Transform(x=100, y=0))

    # Target 2 (Yukkuri) at (200, 0) - Behind Wall - Occluded
    target2 = world.create_entity()
    t2_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t2_body.position = (200, 0)
    t2_shape = pymunk.Circle(t2_body, 10)
    t2_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(t2_body, t2_shape)

    world.add_component(target2, PhysicsBody(body=t2_body, shape=t2_shape))
    world.add_component(target2, Transform(x=200, y=0))

    # Wall between 150, -50 and 150, 50
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_body.position = (150, 0)
    wall_shape = pymunk.Segment(wall_body, (0, -50), (0, 50), 5)
    wall_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.WALL)
    physics_system.space.add(wall_body, wall_shape)

    # Update
    vis_system.update(world, 0.1)

    # Check
    ai = world.get_component(obs, AIState)
    assert target1 in ai.visible_entities
    assert target2 not in ai.visible_entities

def test_visibility_fov():
    world = World()
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)
    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer facing East (1, 0) -> Angle 0
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_body.angle = 0
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(obs_body, obs_shape)

    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0, rotation=0))
    world.add_component(obs, Vision(range=200, fov=90)) # 90 degree FOV (+- 45)
    world.add_component(obs, AIState())

    # Target In Front
    t1 = world.create_entity()
    t1b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t1b.position = (100, 0)
    t1s = pymunk.Circle(t1b, 10)
    t1s.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(t1b, t1s)
    world.add_component(t1, PhysicsBody(body=t1b, shape=t1s))
    world.add_component(t1, Transform(x=100, y=0))

    # Target Behind
    t2 = world.create_entity()
    t2b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t2b.position = (-100, 0)
    t2s = pymunk.Circle(t2b, 10)
    t2s.filter = pymunk.ShapeFilter(categories=CollisionCategories.YUKKURI)
    physics_system.space.add(t2b, t2s)
    world.add_component(t2, PhysicsBody(body=t2b, shape=t2s))
    world.add_component(t2, Transform(x=-100, y=0))

    vis_system.update(world, 0.1)

    ai = world.get_component(obs, AIState)
    assert t1 in ai.visible_entities
    assert t2 not in ai.visible_entities
