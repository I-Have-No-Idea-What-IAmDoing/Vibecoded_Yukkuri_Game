import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.hierarchy_system import HierarchySystem
from yukkuri_game.game.components import Mount, Transform, PhysicsBody, PendingDismount


@pytest.fixture
def world():
    w = World()
    return w


@pytest.fixture
def hierarchy_system():
    return HierarchySystem()


@pytest.fixture
def physics_space():
    return pymunk.Space()


def test_process_entity_hierarchy_update(world, hierarchy_system):
    """Test position updates for mounted entities."""

    # Root
    root = world.create_entity()
    root_trans = Transform(x=100, y=100, rotation=0.0)
    root_mount = Mount(parent_id=-1, children_ids=[])
    world.add_component(root, root_trans)
    world.add_component(root, root_mount)

    # Child
    child = world.create_entity()
    child_trans = Transform(x=0, y=0)
    # Offset (0, -10) relative to parent
    child_mount = Mount(parent_id=root, mount_point_offset=pymunk.Vec2d(0, -10))
    world.add_component(child, child_trans)
    world.add_component(child, child_mount)

    # Link
    root_mount.children_ids.append(child)

    hierarchy_system.update(world, 1.0)

    # Check child position
    assert child_trans.x == 100
    assert child_trans.y == 90  # 100 - 10


def test_process_entity_hierarchy_rotation(world, hierarchy_system):
    """Test position updates with rotation."""

    # Root (Rotated 90 degrees / pi/2)
    root = world.create_entity()
    import math

    root_trans = Transform(x=100, y=100, rotation=math.pi / 2)
    root_mount = Mount(parent_id=-1, children_ids=[])
    world.add_component(root, root_trans)
    world.add_component(root, root_mount)

    # Child
    child = world.create_entity()
    child_trans = Transform(x=0, y=0)
    # Offset (10, 0) relative to parent (local X)
    child_mount = Mount(parent_id=root, mount_point_offset=pymunk.Vec2d(10, 0))
    world.add_component(child, child_trans)
    world.add_component(child, child_mount)

    # Link
    root_mount.children_ids.append(child)

    hierarchy_system.update(world, 1.0)

    # Rotated 90 deg, (10, 0) becomes (0, 10) (assuming standard math rotation)
    # pymunk Vec2d rotated: (x, y).rotated(angle)
    # (10, 0).rotated(pi/2) is roughly (0, 10)

    # Expected: (100, 100) + (0, 10) = (100, 110)
    assert child_trans.x == pytest.approx(100.0)
    assert child_trans.y == pytest.approx(110.0)
    assert child_trans.rotation == pytest.approx(math.pi / 2)


def test_process_dismount_find_spot(world, hierarchy_system, physics_space):
    """Test finding a free spot for dismount."""

    # Entity pending dismount
    e = world.create_entity()
    trans = Transform(x=0, y=0)

    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = (0, 0)
    shape = pymunk.Circle(body, 10)
    shape.sensor = True  # Start as sensor
    physics_space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    pending = PendingDismount()

    world.add_component(e, trans)
    world.add_component(e, phys)
    world.add_component(e, pending)

    # Ensure (0,0) is blocked by a wall
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_body.position = (0, 0)
    wall_shape = pymunk.Circle(wall_body, 10)
    physics_space.add(wall_body, wall_shape)

    # Run update
    hierarchy_system.update(world, 0.1)

    # Should have moved away from (0,0)
    assert (trans.x, trans.y) != (0, 0)
    assert not world.has_component(e, PendingDismount)
    assert not phys.shape.sensor  # Should no longer be a sensor


def test_process_dismount_timeout(world, hierarchy_system, physics_space):
    """Test emergency teleport after timeout."""

    # Entity pending dismount
    e = world.create_entity()
    trans = Transform(x=0, y=0)

    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = (0, 0)
    shape = pymunk.Circle(body, 10)
    shape.sensor = True
    physics_space.add(body, shape)

    phys = PhysicsBody(body=body, shape=shape)
    # Set time > timeout (5.0)
    pending = PendingDismount(time_in_pending=6.0)

    world.add_component(e, trans)
    world.add_component(e, phys)
    world.add_component(e, pending)

    # Block EVERYTHING nearby (simulate stuck)
    # Or just rely on the mock logic.
    # Actually `find_free_spot` logic is hard to mock failures completely without extensive setup.
    # But since we already tested finding spot, let's force a scenario where `find_free_spot` might fail or just rely on the code path.
    # The code checks `if found_pos:`.
    # If we want to test timeout, we need `find_free_spot` to return None.

    # We can patch `find_free_spot` for this test
    original_find = hierarchy_system.find_free_spot
    hierarchy_system.find_free_spot = lambda space, start, shape: None

    try:
        hierarchy_system.update(world, 0.1)

        # Should have forced dismount via emergency teleport
        # Emergency teleport attempts to find spot near (0,0) or defaults to (0,0)
        # Since we mocked find_free_spot to None, it will default to (0,0)

        assert not world.has_component(e, PendingDismount)
        assert not phys.shape.sensor

    finally:
        hierarchy_system.find_free_spot = original_find


def test_structure_update(world, hierarchy_system, physics_space):
    """Test updating the physics structure of the root."""

    # Root
    root = world.create_entity()
    root_body = pymunk.Body(body_type=pymunk.Body.DYNAMIC)
    root_shape = pymunk.Circle(root_body, 10)
    physics_space.add(root_body, root_shape)

    root_phys = PhysicsBody(body=root_body, shape=root_shape)
    root_mount = Mount(parent_id=-1, structure_dirty=True)
    world.add_component(root, root_phys)
    world.add_component(root, root_mount)

    # Child
    child = world.create_entity()
    child_body = pymunk.Body(
        body_type=pymunk.Body.KINEMATIC
    )  # Child body type doesn't matter for proxy
    child_shape = pymunk.Circle(child_body, 5)  # Radius 5
    child_phys = PhysicsBody(body=child_body, shape=child_shape)

    child_mount = Mount(parent_id=root, mount_point_offset=pymunk.Vec2d(0, -20))
    world.add_component(child, child_phys)
    world.add_component(child, child_mount)

    root_mount.children_ids.append(child)

    hierarchy_system.update(world, 0.1)

    # Check if proxy shape added to root body
    assert len(root_body.shapes) == 2  # Original + Proxy

    proxy = None
    for s in root_body.shapes:
        if getattr(s, "is_hierarchy_proxy", False):
            proxy = s
            break

    assert proxy is not None
    assert proxy.radius == 5
    assert proxy.offset == (0, -20)
    assert not root_mount.structure_dirty
