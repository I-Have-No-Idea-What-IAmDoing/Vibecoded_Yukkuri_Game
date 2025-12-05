
import pymunk
import math
from yukkuri_game.game.systems.kinematic_movement_system import KinematicMovementSystem
from yukkuri_game.game.systems.hierarchy_system import HierarchySystem
from yukkuri_game.game.components import PhysicsBody, MovementController, Transform, Mount, PendingDismount
from yukkuri_game.engine.ecs import World

# Mock classes
class MockServiceLocator:
    def __init__(self, physics_system):
        self.physics_system = physics_system

    def try_get(self, service_type):
        if service_type.__name__ == 'PhysicsSystem':
            return self.physics_system
        return None

class MockPhysicsSystem:
    def __init__(self):
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.space.damping = 0.9

class MockWorld(World):
    def __init__(self):
        super().__init__()
        self.services = MockServiceLocator(MockPhysicsSystem())

# Verify Kinematic Movement
def test_kinematic_movement():
    print("Testing Kinematic Movement...")
    world = MockWorld()
    system = KinematicMovementSystem()

    # Setup Entity
    ent = world.create_entity()

    body = pymunk.Body(1, 1, body_type=pymunk.Body.KINEMATIC)
    body.position = (100, 100)
    shape = pymunk.Circle(body, 10)
    world.services.physics_system.space.add(body, shape)

    phys = PhysicsBody(body, shape)
    trans = Transform(100, 100)
    ctrl = MovementController()

    world.add_component(ent, phys)
    world.add_component(ent, trans)
    world.add_component(ent, ctrl)

    # Set input to move right
    ctrl.target_velocity = pymunk.Vec2d(100, 0)

    # Step 1 second
    dt = 1.0/60.0
    for _ in range(60):
        system.update(world, dt)

    print(f"Position after 1s: {body.position}")

    assert body.position.x > 100, "Should have moved right"

    # Test Wall Collision
    print("Testing Wall Collision...")

    # Add wall at x=200
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_body.position = (200, 100)
    wall_shape = pymunk.Poly.create_box(wall_body, (20, 100)) # width 20, height 100. Left edge at 190.
    world.services.physics_system.space.add(wall_body, wall_shape)

    # Reset entity
    body.position = (150, 100)
    ctrl.current_velocity = pymunk.Vec2d(100, 0) # Already moving
    ctrl.target_velocity = pymunk.Vec2d(100, 0)

    # Step until impact
    for _ in range(60):
        system.update(world, dt)

    print(f"Position after hitting wall: {body.position}")

    assert body.position.x < 190, "Should not penetrate wall center"
    assert body.position.x > 170, "Should be close to wall"

# Verify Hierarchy
def test_hierarchy():
    print("\nTesting Hierarchy...")
    world = MockWorld()
    h_system = HierarchySystem()

    # Root
    root = world.create_entity()
    root_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    root_body.position = (100, 100)
    root_shape = pymunk.Circle(root_body, 10)
    world.services.physics_system.space.add(root_body, root_shape)

    world.add_component(root, PhysicsBody(root_body, root_shape))
    world.add_component(root, Transform(100, 100))

    # Child
    child = world.create_entity()
    child_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    child_shape = pymunk.Circle(child_body, 5)
    world.services.physics_system.space.add(child_body, child_shape)

    world.add_component(child, PhysicsBody(child_body, child_shape))
    world.add_component(child, Transform(0, 0)) # Initial doesn't matter

    # Mount
    root_mount = Mount(children_ids=[child])
    child_mount = Mount(parent_id=root, mount_point_offset=pymunk.Vec2d(0, -20)) # On top

    world.add_component(root, root_mount)
    world.add_component(child, child_mount)

    # Run System
    h_system.update(world, 1.0/60.0)

    print(f"Child Pos: {child_body.position}")
    assert child_body.position == pymunk.Vec2d(100, 80), "Child should be at (100, 80)"

    # Rotate Root
    root_body.angle = math.radians(90) # 90 degrees
    # Update
    h_system.update(world, 1.0/60.0)

    print(f"Child Pos after Rotation: {child_body.position}")

    # Floating point comparison
    assert abs(child_body.position.x - 120) < 0.1
    assert abs(child_body.position.y - 100) < 0.1

if __name__ == "__main__":
    test_kinematic_movement()
    test_hierarchy()
