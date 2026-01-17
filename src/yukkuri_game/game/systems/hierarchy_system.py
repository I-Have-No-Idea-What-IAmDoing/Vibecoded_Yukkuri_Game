"""
Hierarchy System - Parent-Child Mount Management.

Manages mounted entity relationships where one Yukkuri can carry another.
Handles the "Totem Pole" stacking mechanic and safe dismounting.

Mounting Mechanics:
- Mounted children follow parent position with offset rotation
- Root entity's physics body gets proxy shapes for all children
- Mounted entities' own shapes become sensors (no collision)

Dismounting:
- When unmounting, entities need to find free space to land
- Uses spiral search pattern to find collision-free position
- Emergency teleport to origin if no space found within timeout

Composite Collider:
- Root body accumulates proxy shapes for each mounted child
- Allows proper collision for entire stack while treating it as one unit
- Structure rebuilt when mount hierarchy changes (structure_dirty flag)
"""

import pymunk
import math
from ...engine import rng
from loguru import logger
from ...engine.ecs import System, World
from ..components import (
    Mount,
    Transform,
    PhysicsBody,
    PendingDismount,
)
from ..collision_constants import CollisionCategories

# ==================== DISMOUNT SEARCH CONSTANTS ====================
# Controls the spiral search pattern for finding free landing spots

_DISMOUNT_DEFAULT_RADIUS = 10.0  # Default entity collision radius if unknown
_DISMOUNT_MAX_SEARCH_RADIUS = 100.0  # Maximum spiral search distance
_DISMOUNT_MAX_SEARCH_CHECKS = 20  # Maximum positions to check before giving up
_DISMOUNT_TIMEOUT = 5.0  # Seconds before emergency teleport triggers
_DEFAULT_ENTITY_RADIUS = 10.0  # Fallback entity size for proxy shapes
_SPIRAL_SEARCH_MIN_RADIUS = 0.1  # Prevents division by zero in spiral calc


class HierarchySystem(System):
    """
    Updates positions of mounted entities based on their parents.
    Also handles Dismount logic (finding free space).
    """

    def update(self, world: World, dt: float) -> None:
        """
        Recursive update of the hierarchy.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
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

    def process_structure_update(
        self, world: World, root_entity: int, mounts: dict[int, Mount]
    ) -> None:
        """
        Updates the Root's physics body shapes to represent the stack ("The Totem Pole").
        Instead of one giant circle, we create a Composite Collider.

        Args:
            world (World): The ECS World.
            root_entity (int): The root entity ID.
            mounts (dict): Dictionary of all Mount components.

        Returns:
            None
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

        body = phys.body
        space = body.space

        # Remove old proxy shapes
        to_remove = []
        for shape in body.shapes:
            if hasattr(shape, "is_hierarchy_proxy"):
                to_remove.append(shape)

        if space:
            for s in to_remove:
                space.remove(s)

        # Now add new shapes for children
        # Traverse hierarchy
        stack = [(root_entity, pymunk.Vec2d(0, 0))]

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
                proxy_radius = _DEFAULT_ENTITY_RADIUS
                if c_phys and hasattr(c_phys.shape, "radius"):
                    proxy_radius = c_phys.shape.radius

                # Create Circle at offset
                new_shape = pymunk.Circle(body, proxy_radius, child_total_offset)
                new_shape.friction = 0.0  # Root movement logic handles friction.
                new_shape.elasticity = 0.0
                new_shape.is_hierarchy_proxy = True

                # Inherit filter from root, but maybe ensure it blocks?
                new_shape.filter = phys.shape.filter

                if space:
                    space.add(new_shape)

                stack.append((child_id, child_total_offset))

        mount.structure_dirty = False

    def process_entity(
        self, world: World, root_entity: int, mounts: dict[int, Mount]
    ) -> None:
        """
        Iteratively update children of this entity using a stack.

        Args:
            world (World): The ECS World.
            root_entity (int): The root entity ID.
            mounts (dict): Dictionary of all Mount components.

        Returns:
            None
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
            root_prev_pos = (
                pymunk.Vec2d(
                    trans.prev_x if trans.prev_x is not None else 0.0,
                    trans.prev_y if trans.prev_y is not None else 0.0,
                )
                if trans.prev_x is not None and trans.prev_y is not None
                else root_pos
            )
            root_prev_rot = (
                trans.prev_rotation if trans.prev_rotation is not None else root_rot
            )

        if root_pos is None:
            return

        if root_prev_pos is None:
            root_prev_pos = root_pos

        stack = [(root_entity, root_pos, root_rot, root_prev_pos, root_prev_rot)]

        while stack:
            current_entity, parent_pos, parent_rot, parent_prev_pos, parent_prev_rot = (
                stack.pop()
            )

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

                    # Child's own shape becomes sensor; Root's proxy handles collision.
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

                stack.append(
                    (child_id, child_pos, child_rot, child_prev_pos, child_prev_rot)
                )

    def process_dismounts(self, world: World, dt: float) -> None:
        """
        Handle entities that need to be placed back into the world.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
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
                    logger.warning(
                        f"Entity {entity} forced dismount after timeout. Attempting Emergency Teleport."
                    )
                    self._emergency_teleport(space, phys, trans)

                    if phys.shape.sensor:
                        phys.shape.sensor = False
                    to_remove.append(entity)

        for ent in to_remove:
            world.remove_component(ent, PendingDismount)

    def _emergency_teleport(
        self, space: pymunk.Space, phys: PhysicsBody, trans: Transform
    ) -> None:
        """
        Attempts to teleport the entity to a safe fallback location (0,0).
        In a real game, this would query for SpawnPoints or Base entities.

        Args:
            space (pymunk.Space): The physics space.
            phys (PhysicsBody): The physics component.
            trans (Transform): The transform component.

        Returns:
            None
        """
        # Fallback to origin. If no free spot, depenetration will handle it.
        fallback_pos = pymunk.Vec2d(0, 0)
        final_pos = self.find_free_spot(space, fallback_pos, phys.shape) or fallback_pos

        phys.body.position = final_pos
        trans.x = final_pos.x
        trans.y = final_pos.y

    def find_free_spot(
        self, space: pymunk.Space, start_pos: pymunk.Vec2d, shape: pymunk.Shape
    ) -> pymunk.Vec2d | None:
        """
        Searches for a free spot using a spiral pattern.
        Uses point_query (or reusing the same temp shape if possible) to ensure the full volume fits.
        Optimized to reduce garbage creation.

        Args:
            space (pymunk.Space): The physics space.
            start_pos (pymunk.Vec2d): The starting position to search from.
            shape (pymunk.Shape): The shape of the entity.

        Returns:
            Optional[pymunk.Vec2d]: A free position, or None if not found.
        """
        max_radius = _DISMOUNT_MAX_SEARCH_RADIUS
        current_r = 0.0
        theta = 0.0

        collider_radius = _DISMOUNT_DEFAULT_RADIUS
        if hasattr(shape, "radius") and shape.radius > 0:
            collider_radius = shape.radius
            # If poly, approximate radius?
            bb = shape.cache_bb()
            width = bb.right - bb.left
            height = bb.top - bb.bottom
            collider_radius = math.hypot(
                width / 2.0, height / 2.0
            )  # Circumscribed circle.

        step_size = collider_radius * 2.0
        max_checks = _DISMOUNT_MAX_SEARCH_CHECKS
        checks = 0

        # Optimization: Use point_query with radius (Capsule/Circle Check) instead of creating temp bodies.
        # This is much faster and cleaner.
        # Effectively checks if a circle of `collider_radius` at `pos` hits anything.

        # Filter: Match what the entity would collide with (Walls, Other Yukkuris)
        query_filter = pymunk.ShapeFilter(
            mask=CollisionCategories.HIGH_OBSTACLE | CollisionCategories.GROUND_UNIT
        )

        def is_spot_free(pos: pymunk.Vec2d) -> bool:
            # point_query simulates circle collider at pos.
            infos = space.point_query(pos, collider_radius, query_filter)
            valid_hits = [i for i in infos if i.shape != shape and not i.shape.sensor]
            return len(valid_hits) == 0

        if is_spot_free(start_pos):
            return start_pos

        theta = rng.random_float() * 2 * math.pi

        while current_r < max_radius and checks < max_checks:
            checks += 1
            offset = pymunk.Vec2d(
                current_r * math.cos(theta), current_r * math.sin(theta)
            )
            candidate = start_pos + offset

            if is_spot_free(candidate):
                return candidate

            arc = collider_radius
            d_theta = arc / (
                current_r if current_r > _SPIRAL_SEARCH_MIN_RADIUS else 1.0
            )
            theta += d_theta
            current_r = (step_size / (2 * math.pi)) * theta

        return None
