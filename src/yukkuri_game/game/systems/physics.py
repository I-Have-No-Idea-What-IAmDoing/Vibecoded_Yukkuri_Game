import pymunk
from ...engine.ecs import System, World
from ..components import Transform, PhysicsBody

class PhysicsSystem(System):
    """
    System responsible for stepping the physics simulation and syncing with Transform components.

    Attributes:
        space (pymunk.Space): The pymunk physics space.
        accumulator (float): Time accumulator for fixed time step.
        time_step (float): The fixed time step for physics (default 1/60).
    """

    def __init__(self, gravity: tuple[float, float] = (0, 0)):
        """
        Initializes the PhysicsSystem.

        Args:
            gravity (tuple[float, float]): The gravity vector (x, y). Defaults to (0, 0) for top-down.
        """
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 0.9 # Add damping to simulate friction/air resistance
        self.accumulator = 0.0
        self.time_step = 1.0 / 60.0
        self.max_frame_time = 0.25

    def update(self, world: World, dt: float) -> None:
        """
        Updates the physics simulation.

        Steps the pymunk space and syncs PhysicsBody positions to Transform components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        # Clamp dt to avoid spiral of death with high time scales or lag
        if dt > self.max_frame_time:
            dt = self.max_frame_time

        self.accumulator += dt
        while self.accumulator >= self.time_step:
            self.space.step(self.time_step)
            self.accumulator -= self.time_step

        # Sync PhysicsBody -> Transform
        for entity, (phys, trans) in world.get_components_tuple(PhysicsBody, Transform):
            trans.x = phys.body.position.x
            trans.y = phys.body.position.y
            # Rotation could also be synced if Transform supported it
