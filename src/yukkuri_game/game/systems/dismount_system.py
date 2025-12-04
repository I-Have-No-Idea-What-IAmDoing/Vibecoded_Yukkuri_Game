"""
Dismount System.
"""
import math
import pymunk
from ...engine.ecs import System, World
from ..components import Transform, PendingDismount, PhysicsBody
from ..systems.physics import PhysicsSystem

class DismountSystem(System):
    """
    Handles entities searching for a safe spot to dismount/spawn (Ghost Mode).
    """

    def __init__(self):
        super().__init__()
        self.physics_system = None
        self.space = None

    def update(self, world: World, dt: float) -> None:
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)
            if self.physics_system:
                self.space = self.physics_system.space

        if not self.space:
            return

        for entity, (transform, pending, phys) in world.get_components_tuple(Transform, PendingDismount, PhysicsBody):
            pending.elapsed_time += dt
            pending.retry_timer -= dt

            if pending.retry_timer <= 0:
                # Try to find a spot
                if self.find_and_place(entity, transform, phys):
                    world.remove_component(entity, PendingDismount)
                    self.space.reindex_shapes_for_body(phys.body)
                else:
                    pending.retry_timer = 0.5 # Retry every 0.5s

            if pending.elapsed_time > 10.0:
                # Emergency Teleport logic would go here
                pass

    def find_and_place(self, entity, transform, phys):
        start_x, start_y = transform.x, transform.y
        radius = 10.0
        if isinstance(phys.shape, pymunk.Circle):
            radius = phys.shape.radius

        MAX_STEPS = 5
        STEP_SIZE = radius * 2.5

        # Check 0 first
        if self.is_safe(start_x, start_y, radius, phys):
            return True

        for i in range(1, MAX_STEPS + 1):
            count = 8 * i
            angle_step = math.pi * 2 / count
            dist = i * STEP_SIZE

            for j in range(count):
                angle = j * angle_step
                cx = start_x + math.cos(angle) * dist
                cy = start_y + math.sin(angle) * dist

                if self.is_safe(cx, cy, radius, phys):
                    transform.x = cx
                    transform.y = cy
                    phys.body.position = (cx, cy)
                    return True

        return False

    def is_safe(self, x, y, radius, own_phys):
        original_pos = own_phys.body.position

        # Temporarily move
        own_phys.body.position = (x, y)
        self.space.reindex_shapes_for_body(own_phys.body)

        overlaps = self.space.shape_query(own_phys.shape)

        is_clear = True
        for contact in overlaps:
             # Pymunk returns ShapeQueryInfo objects
             hit_shape = getattr(contact, 'shape', None)

             if not hit_shape:
                 continue

             if not hit_shape.sensor and hit_shape != own_phys.shape:
                 is_clear = False
                 break

        if not is_clear:
             own_phys.body.position = original_pos
             self.space.reindex_shapes_for_body(own_phys.body)

        return is_clear
