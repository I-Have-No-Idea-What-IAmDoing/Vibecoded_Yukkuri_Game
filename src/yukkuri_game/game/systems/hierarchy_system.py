"""
Hierarchy System.
"""
from ...engine.ecs import System, World
from ..components import Transform, Mount, PhysicsBody, PendingDismount
from ..systems.physics import PhysicsSystem
import pymunk

class HierarchySystem(System):
    """
    Manages parent-child relationships and mounting.
    """

    def update(self, world: World, dt: float) -> None:
        # Iterate over entities with Mount component that have a parent
        for entity, (mount, transform) in world.get_components_tuple(Mount, Transform):
            if mount.parent_id != -1:
                self.update_child(world, entity, mount, transform)

    def update_child(self, world, entity, mount, transform):
        if not world.entity_exists(mount.parent_id):
            # Parent destroyed. Enter Ghost Mode.
            world.add_component(entity, PendingDismount(retry_timer=0.0))
            mount.parent_id = -1
            return

        parent_trans = world.get_component(mount.parent_id, Transform)
        if not parent_trans:
            return

        parent_phys = world.get_component(mount.parent_id, PhysicsBody)
        rotation = 0
        if parent_phys:
            rotation = parent_phys.body.angle

        # Rotate offset
        offset = mount.mount_point_offset
        if rotation != 0:
            offset = offset.rotated(rotation)

        target_x = parent_trans.x + offset.x
        target_y = parent_trans.y + offset.y

        transform.x = target_x
        transform.y = target_y

        # Sync physics body if exists
        phys = world.get_component(entity, PhysicsBody)
        if phys:
            phys.body.position = (transform.x, transform.y)
            # Ensure it is sensor?
            if not phys.shape.sensor:
                 phys.shape.sensor = True
