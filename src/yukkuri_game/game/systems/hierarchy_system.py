"""
Hierarchy System.
Manages parent-child relationships and transforms.
Optimized to handle dismounts and structure updates more efficiently.
"""

import pymunk
import math
import random
from loguru import logger
from ...engine.ecs import System, World
from ..components import Mount, Transform, PhysicsBody, PendingDismount, MovementController
from ..collision_constants import CollisionCategories
from .physics import PhysicsSystem

_DISMOUNT_DEFAULT_RADIUS = 10.0
_DISMOUNT_MAX_SEARCH_RADIUS = 100.0
_DISMOUNT_MAX_SEARCH_CHECKS = 20
_DISMOUNT_TIMEOUT = 5.0
_DEFAULT_ENTITY_RADIUS = 10.0
_SPIRAL_SEARCH_MIN_RADIUS = 0.1

class HierarchySystem(System):
    """
    Updates positions of mounted entities based on their parents.
    Also handles Dismount logic (finding free space).
    """

    def update(self, world: World, dt: float) -> None:
        """
        Recursive update of the hierarchy.
        """
        # 1. Build a map of all mounted entities
        mounts = world.get_components(Mount)

        # 2. Identify roots
        roots = []
        for ent, mount in mounts.items():
            if mount.parent_id == -1:
                roots.append(ent)
            elif mount.parent_id not in mounts:
                roots.append(ent)

        # 3. Process roots
        for root in roots:
            self.process_structure_update(world, root, mounts)
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts
        self.process_dismounts(world, dt)

    def process_structure_update(self, world: World, root_entity: int, mounts: dict):
        """
        Updates the Root's physics body shapes to represent the stack ("The Totem Pole").
        Instead of one giant circle, we create a Composite Collider.
        """
        mount = mounts.get(root_entity)
        if not mount or not mount.structure_dirty:
            return

        phys = world.get_component(root_entity, PhysicsBody)
        if not phys:
            return

        # We need to rebuild the shapes on the root body.
        # Strategy:
        # 1. Keep the original shape (the root unit).
        # 2. Remove any "Child Proxy" shapes from previous updates.
        # 3. Add new shapes for current children.

        # NOTE: Pymunk doesn't let us tag shapes easily as "Child Proxy" without custom attributes.
        # We assume shapes[0] is the main one? Or we can use `shape.info`?
        # Pymunk shapes have `filter`.
        # Let's assume the first shape is the Unit's own shape and others are added.
        # WARNING: This is destructive if not careful.

        # Simpler approach for this specific proposal critique:
        # The proposal said "The Root maintains a simple Bounding Circle or Capsule".
        # The Critique said "That fails for wide stacks".
        # The Fix is "Composite Collider".

        # Implementation:
        # 1. Clear extra shapes.
        # 2. Add shapes at offsets.

        # We need to identify which shapes are "structural additions".
        # Let's use a dynamic attribute on the shape.

        body = phys.body
        space = body.space

        # Remove old proxy shapes
        to_remove = []
        for shape in body.shapes:
            if hasattr(shape, 'is_hierarchy_proxy'):
                to_remove.append(shape)

        for s in to_remove:
            if space: space.remove(s)
            # body.shapes is read-only? No, space.remove(s) removes it from space.
            # We must remove it from body too? Pymunk handles this when we remove from space usually?
            # Actually, we might need to remove from body explicitly if not in space yet.
            pass

        # Pymunk bodies don't allow removing shapes directly via list manipulation easily?
        # `space.remove(shape)` removes it from simulation.
        # If the body is not in space, we might be stuck.
        # Assuming body is in space.

        if space:
            for s in to_remove:
                space.remove(s)

        # Now add new shapes for children
        # Traverse hierarchy
        stack = [(root_entity, pymunk.Vec2d(0,0))]

        while stack:
            curr_ent, curr_offset = stack.pop()
            curr_mount = mounts.get(curr_ent)
            if not curr_mount:
                continue

            for child_id in curr_mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                child_total_offset = curr_offset + child_mount.mount_point_offset

                # Create a proxy shape for this child on the Root Body
                c_phys = world.get_component(child_id, PhysicsBody)
                child_radius = _DEFAULT_ENTITY_RADIUS
                if c_phys and hasattr(c_phys.shape, 'radius'):
                    child_radius = c_phys.shape.radius

                # Create Circle at offset
                new_shape = pymunk.Circle(body, child_radius, child_total_offset)
                new_shape.friction = 0.0 # Friction handled by root movement logic usually
                new_shape.elasticity = 0.0
                new_shape.is_hierarchy_proxy = True

                # Inherit filter from root, but maybe ensure it blocks?
                new_shape.filter = phys.shape.filter

                if space:
                    space.add(new_shape)

                stack.append((child_id, child_total_offset))

        mount.structure_dirty = False

    def process_entity(self, world: World, root_entity: int, mounts: dict):
        """
        Iteratively update children of this entity using a stack.
        """
        root_pos = None
        root_rot = 0.0
        root_prev_pos = None
        root_prev_rot = 0.0

        phys = world.get_component(root_entity, PhysicsBody)
        if phys:
            root_pos = phys.body.position
            root_rot = phys.body.angle
        else:
            trans = world.get_component(root_entity, Transform)
            if trans:
                root_pos = pymunk.Vec2d(trans.x, trans.y)
                root_rot = trans.rotation

        trans = world.get_component(root_entity, Transform)
        if trans:
            root_prev_pos = pymunk.Vec2d(trans.prev_x, trans.prev_y) if trans.prev_x is not None else root_pos
            root_prev_rot = trans.prev_rotation if trans.prev_rotation is not None else root_rot

        if root_pos is None:
            return

        if root_prev_pos is None:
            root_prev_pos = root_pos

        stack = [(root_entity, root_pos, root_rot, root_prev_pos, root_prev_rot)]

        while stack:
            current_entity, parent_pos, parent_rot, parent_prev_pos, parent_prev_rot = stack.pop()

            mount = mounts.get(current_entity)
            if not mount:
                continue

            for child_id in mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                # Calculate Child Position
                offset = child_mount.mount_point_offset
                rotated_offset = offset.rotated(parent_rot)
                child_pos = parent_pos + rotated_offset

                # Calculate Child Prev Position
                prev_rotated_offset = offset.rotated(parent_prev_rot)
                child_prev_pos = parent_prev_pos + prev_rotated_offset

                # Apply to Child
                child_phys = world.get_component(child_id, PhysicsBody)
                child_rot = parent_rot
                child_prev_rot = parent_prev_rot

                if child_phys:
                    child_phys.body.position = child_pos
                    child_phys.body.angle = child_rot

                    # Ensure child's OWN body is sensor (Hitbox only)
                    # The physical collision is handled by the Root's Proxy Shapes now.
                    if not child_phys.shape.sensor:
                        child_phys.shape.sensor = True

                child_trans = world.get_component(child_id, Transform)
                if child_trans:
                    child_trans.x = child_pos.x
                    child_trans.y = child_pos.y
                    child_trans.rotation = child_rot
                    child_trans.prev_x = child_prev_pos.x
                    child_trans.prev_y = child_prev_pos.y
                    child_trans.prev_rotation = child_prev_rot

                stack.append((child_id, child_pos, child_rot, child_prev_pos, child_prev_rot))

    def process_dismounts(self, world: World, dt: float):
        """
        Handle entities that need to be placed back into the world.
        """
        components = world.get_components_tuple(PendingDismount, Transform, PhysicsBody)

        to_remove = []

        for entity, (pending, trans, phys) in components:
            pending.time_in_pending += dt

            if not phys.shape.sensor:
                phys.shape.sensor = True

            space = phys.body.space
            if not space:
                continue

            start_pos = phys.body.position

            # Use Volume Query instead of Center Point
            found_pos = self.find_free_spot(space, start_pos, phys.shape)

            if found_pos:
                phys.body.position = found_pos
                trans.x = found_pos.x
                trans.y = found_pos.y

                if phys.shape.sensor:
                    phys.shape.sensor = False

                to_remove.append(entity)
            else:
                if pending.time_in_pending > _DISMOUNT_TIMEOUT:
                    if phys.shape.sensor:
                        phys.shape.sensor = False
                    to_remove.append(entity)
                    logger.warning(f"Entity {entity} forced dismount after timeout.")

        for ent in to_remove:
            world.remove_component(ent, PendingDismount)

    def find_free_spot(self, space, start_pos, shape):
        """
        Searches for a free spot using a spiral pattern.
        Uses shape_query to ensure the full volume fits.
        """
        max_radius = _DISMOUNT_MAX_SEARCH_RADIUS
        current_r = 0.0
        theta = 0.0

        collider_radius = _DISMOUNT_DEFAULT_RADIUS
        if hasattr(shape, 'radius'):
            collider_radius = shape.radius

        step_size = collider_radius * 2.0
        max_checks = _DISMOUNT_MAX_SEARCH_CHECKS
        checks = 0

        # Temporary body for queries
        temp_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        temp_shape = pymunk.Circle(temp_body, collider_radius) # Approx if shape is complex
        temp_shape.filter = pymunk.ShapeFilter(mask=CollisionCategories.WALL | CollisionCategories.YUKKURI)

        def is_spot_free(pos):
             temp_body.position = pos
             # shape_query returns a list of contact points if overlapping
             infos = space.shape_query(temp_shape)
             # Filter out our own real body if it happens to be hit (shouldn't be, it's sensor)
             valid_hits = [i for i in infos if i.shape != shape and not i.shape.sensor]
             return len(valid_hits) == 0

        if is_spot_free(start_pos):
             return start_pos

        theta = random.uniform(0, 2 * math.pi)

        while current_r < max_radius and checks < max_checks:
            checks += 1
            offset = pymunk.Vec2d(current_r * math.cos(theta), current_r * math.sin(theta))
            candidate = start_pos + offset

            if is_spot_free(candidate):
                return candidate

            arc = collider_radius
            d_theta = arc / (current_r if current_r > _SPIRAL_SEARCH_MIN_RADIUS else 1.0)
            theta += d_theta
            current_r = (step_size / (2*math.pi)) * theta

        return None
