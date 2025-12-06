import pymunk
from src.yukkuri_game.game.systems.kinematic_movement_system import KinematicMovementSystem
from src.yukkuri_game.game.components import PhysicsBody, MovementController, Transform
from src.yukkuri_game.engine.ecs import World
from dataclasses import dataclass

@dataclass
class MockServiceLocator:
    def try_get(self, type_):
        return None

class MockWorld(World):
    def __init__(self):
        super().__init__()
        self.services = MockServiceLocator()

def test_hallway_movement():
    # Setup Pymunk Space
    space = pymunk.Space()
    space.gravity = (0, 0)

    # Create Wall (Hallway)
    # Wall from (0, 10) to (100, 10)
    # And (0, -10) to (100, -10)
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_shape1 = pymunk.Segment(wall_body, (0, 10), (100, 10), 1)
    wall_shape2 = pymunk.Segment(wall_body, (0, -10), (100, -10), 1)
    space.add(wall_body, wall_shape1, wall_shape2)

    # Create Character
    body = pymunk.Body(1, 1, body_type=pymunk.Body.KINEMATIC)
    body.position = (10, 0)
    shape = pymunk.Circle(body, 5)
    space.add(body, shape)

    # Components
    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController(acceleration=100.0, friction=10.0)
    controller.target_velocity = pymunk.Vec2d(50, 0) # Moving right
    trans = Transform(x=10, y=0)

    # System
    kms = KinematicMovementSystem()
    kms.space = space

    # Step
    dt = 1.0/60.0

    # print(f"Start Pos: {body.position}")

    for _ in range(60): # 1 second
        kms.move_and_slide(phys, controller, trans, dt)

    print(f"End Pos: {body.position}")
    # We expect roughly 47.5 based on calculation (10 + 37.5)
    assert body.position.x > 45
    assert abs(body.position.y) < 0.1 # Should stay centered

def test_corner_collision():
    # Setup Pymunk Space
    space = pymunk.Space()
    space.gravity = (0, 0)

    # Create Corner (0,0) -> (0, 100) and (0,0) -> (100, 0)
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_shape1 = pymunk.Segment(wall_body, (0, 0), (0, 100), 1)
    wall_shape2 = pymunk.Segment(wall_body, (0, 0), (100, 0), 1)
    space.add(wall_body, wall_shape1, wall_shape2)

    # Create Character at (10, 10) moving towards (-10, -10)
    body = pymunk.Body(1, 1, body_type=pymunk.Body.KINEMATIC)
    body.position = (10, 10)
    shape = pymunk.Circle(body, 5)
    space.add(body, shape)

    # Components
    phys = PhysicsBody(body=body, shape=shape)
    controller = MovementController(acceleration=1000.0, friction=0.0)
    controller.target_velocity = pymunk.Vec2d(-50, -50) # Moving diagonal into corner
    trans = Transform(x=10, y=10)

    # System
    kms = KinematicMovementSystem()
    kms.space = space

    dt = 1.0/60.0

    # print(f"Corner Start Pos: {body.position}")
    for _ in range(30):
        kms.move_and_slide(phys, controller, trans, dt)

    print(f"Corner Pos: {body.position}")

    # Should stop near corner
    # Expected stop: x>=6, y>=6.

    assert body.position.x >= 5.9
    assert body.position.y >= 5.9

    # Also check max distance to corner
    # dist_sq = (body.position.x - 6)**2 + (body.position.y - 6)**2
    # print(f"Distance to expected stop (6,6): {dist_sq}")
    # assert dist_sq < 25.0

if __name__ == "__main__":
    test_hallway_movement()
    test_corner_collision()
