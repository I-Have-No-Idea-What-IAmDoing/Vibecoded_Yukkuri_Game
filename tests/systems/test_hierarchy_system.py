
import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.hierarchy_system import HierarchySystem
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import PhysicsBody, Transform, Mount

def test_hierarchy_movement():
    world = World()

    # Setup Physics (HierarchySystem uses PhysicsBody)
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    hierarchy = HierarchySystem()
    world.add_system(hierarchy)

    # Create Root
    root = world.create_entity()
    root_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    root_body.position = (100, 100)
    root_shape = pymunk.Circle(root_body, 10)
    physics_system.space.add(root_body, root_shape)

    world.add_component(root, PhysicsBody(body=root_body, shape=root_shape))
    world.add_component(root, Transform(x=100, y=100))
    world.add_component(root, Mount())

    # Create Child
    child = world.create_entity()
    child_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    child_body.position = (100, 100)
    child_shape = pymunk.Circle(child_body, 5)
    physics_system.space.add(child_body, child_shape)

    world.add_component(child, PhysicsBody(body=child_body, shape=child_shape))
    world.add_component(child, Transform(x=100, y=100))
    world.add_component(child, Mount(parent_id=root, mount_point_offset=pymunk.Vec2d(0, 20)))

    # Link
    root_mount = world.get_component(root, Mount)
    root_mount.children_ids.append(child)
    root_mount.structure_dirty = True

    # Update Hierarchy
    hierarchy.update(world, 0.1)

    # Check Child Position (Should be at Root + Offset)
    # Root (100, 100) + Offset (0, 20) -> (100, 120)
    child_phys = world.get_component(child, PhysicsBody)
    assert child_phys.body.position.x == 100
    assert child_phys.body.position.y == 120

    # Check Child Sensor (Should be sensor)
    assert child_phys.shape.sensor == True

    # Check Root Radius (Should be expanded)
    # Base 10. Child at 20 dist + 5 radius = 25.
    root_phys = world.get_component(root, PhysicsBody)
    assert root_phys.shape.radius == 25.0

    # Move Root
    root_body.position = (200, 200)
    root_body.angle = 1.570796 # 90 degrees

    hierarchy.update(world, 0.1)

    # Check Child Position
    # Root (200, 200). Rot 90 deg. Offset (0, 20) rotated 90 -> (-20, 0)
    # Result -> (180, 200)
    # Note: Pymunk angle is radians.

    assert abs(child_phys.body.position.x - 180) < 0.1
    assert abs(child_phys.body.position.y - 200) < 0.1
    assert abs(child_phys.body.angle - 1.570796) < 0.001
