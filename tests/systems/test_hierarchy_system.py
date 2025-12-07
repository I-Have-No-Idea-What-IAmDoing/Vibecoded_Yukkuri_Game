
import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.hierarchy_system import HierarchySystem
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import PhysicsBody, Mount, Transform

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

    # Check Root Body Shapes (Composite Collider)
    # Original shape + Proxy shape for child
    root_phys = world.get_component(root, PhysicsBody)
    assert len(root_phys.body.shapes) == 2

    # Verify one shape is the proxy
    proxy_shapes = [s for s in root_phys.body.shapes if hasattr(s, 'is_hierarchy_proxy')]
    assert len(proxy_shapes) == 1

    # Verify proxy position (relative to body)
    # Body is at (100, 100). Child is at (100, 120).
    # Proxy offset should be (0, 20).
    # Note: Pymunk Circle offset is local.
    proxy = proxy_shapes[0]
    assert proxy.offset.x == 0
    assert proxy.offset.y == 20
    assert proxy.radius == 5 # Child radius
