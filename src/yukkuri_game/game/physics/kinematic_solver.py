"""
Kinematic Solver - Pure Physics Logic.

Extracts the 'sweep-and-slide' and penetration resolution logic from the system
to allow for easier testing and usage outside of the ECS cycle.
"""

import math
import pymunk

from ..components import MovementController, PhysicsBody, Transform


class FakeHit:
    """Synthetic hit result for fallback overlap detection."""

    def __init__(self, normal: pymunk.Vec2d, alpha: float) -> None:
        self.normal = normal
        self.alpha = alpha


class KinematicSolver:
    """
    Solves kinematic movement queries.
    """

    def __init__(self, space: pymunk.Space | None = None):
        self.space = space
        self.skin_width = 0.01
        self._poly_radius_cache: dict[pymunk.Poly, float] = {}

    def set_space(self, space: pymunk.Space) -> None:
        """Sets the physics space reference."""
        self.space = space

    def move_and_slide(
        self,
        phys: PhysicsBody,
        controller: MovementController,
        trans: Transform,
        dt: float,
        agility: float = 1.0,
    ) -> float:
        """
        Executes the sweep-and-slide movement algorithm.
        """
        body = phys.body
        start_pos = body.position

        # 1. Virtual Physics Integration
        input_vector = controller.target_velocity
        velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            friction = controller.friction
            damping = max(0.0, 1.0 - friction * dt)
            velocity = velocity * damping
            if velocity.length_squared < 0.0001:
                velocity = pymunk.Vec2d(0, 0)
        else:
            diff = input_vector - velocity
            change = controller.acceleration * agility * dt
            if change >= diff.length:
                velocity = input_vector
            else:
                velocity += diff.normalized() * change

        controller.current_velocity = velocity

        # 2. Sweep Movement
        move_delta = velocity * dt
        if move_delta.length_squared < 0.000001:
            return 0.0

        current_pos = body.position

        # Rigorous Slide Logic
        max_slides = 5

        for i in range(max_slides):
            if move_delta.length_squared < 0.000001:
                break

            target_pos = current_pos + move_delta
            best_hit: pymunk.SegmentQueryInfo | FakeHit | None = None
            best_alpha = 1.0

            for shape in body.shapes:
                if shape.sensor:
                    continue

                radius = 0.0
                if hasattr(shape, "radius") and shape.radius > 0:
                    radius = shape.radius
                elif isinstance(shape, pymunk.Poly):
                    radius = self._get_poly_radius(shape)

                shape_offset = getattr(shape, "offset", pymunk.Vec2d(0, 0))
                rotated_offset = shape_offset.rotated(body.angle)
                shape_center_world = current_pos + rotated_offset
                shape_dest = shape_center_world + move_delta

                if not self.space:
                    return 0.0

                results = self.space.segment_query(
                    shape_center_world, shape_dest, radius, shape.filter
                )

                for info in results:
                    if info.shape.body == body or info.shape.sensor:
                        continue

                    if info.normal.dot(move_delta) > 0.0001:
                        continue

                    if info.alpha < best_alpha:
                        best_alpha = info.alpha
                        best_hit = info

            # Fallback overlap check
            if best_hit is None:
                original_pos = body.position
                if not self.space:
                    break

                body.position = target_pos
                self.space.reindex_shapes_for_body(body)

                found_overlap = False
                fallback_normal = pymunk.Vec2d(0, 0)

                for shape in body.shapes:
                    if shape.sensor:
                        continue

                    if not self.space:
                        continue
                    infos = self.space.shape_query(shape)
                    for info in infos:
                        if info.shape.body == body or info.shape.sensor:
                            continue

                        contact_set = info.contact_point_set
                        if len(contact_set.points) > 0:
                            min_dist = 0.0
                            for p in contact_set.points:
                                if p.distance < min_dist:
                                    min_dist = p.distance

                            if min_dist < -0.001:
                                normal = contact_set.normal
                                surface_normal = -normal

                                if surface_normal.dot(move_delta) < 0:
                                    found_overlap = True
                                    fallback_normal = surface_normal
                                    break
                    if found_overlap:
                        break

                body.position = original_pos
                if self.space:
                    self.space.reindex_shapes_for_body(body)

                if found_overlap:
                    best_alpha = 0.0
                    best_hit = FakeHit(fallback_normal, 0.0)

            if best_hit:
                md_len = move_delta.length
                safe_alpha = (
                    max(0.0, best_hit.alpha - (self.skin_width / md_len))
                    if md_len > 0.0001
                    else 0.0
                )

                step_move = move_delta * safe_alpha
                current_pos += step_move

                remainder = move_delta * (1.0 - safe_alpha)
                dot = remainder.dot(best_hit.normal)
                remainder = remainder - best_hit.normal * dot

                move_delta = remainder

                v_dot = velocity.dot(best_hit.normal)
                velocity = velocity - best_hit.normal * v_dot

            else:
                current_pos += move_delta
                move_delta = pymunk.Vec2d(0, 0)
                break

        phys.body.position = current_pos
        controller.current_velocity = velocity
        phys.body.velocity = velocity

        return (body.position - start_pos).length

    def resolve_penetration(self, phys: PhysicsBody, pos: pymunk.Vec2d) -> pymunk.Vec2d:
        """
        Checks if the body is currently overlapping static geometry and pushes it out.
        """
        current_pos = pos
        max_iterations = 3

        for iter_idx in range(max_iterations):
            phys.body.position = current_pos
            if phys.body.space:
                phys.body.space.reindex_shapes_for_body(phys.body)

            total_push = pymunk.Vec2d(0, 0)
            hits = 0

            if not self.space:
                break

            for shape in phys.body.shapes:
                infos = self.space.shape_query(shape)
                if not infos:
                    continue

                for info in infos:
                    if info.shape.body == phys.body or info.shape.sensor:
                        continue

                    if info.shape.sensor:
                        continue

                    contact_set = info.contact_point_set
                    if len(contact_set.points) == 0:
                        continue

                    best_push = pymunk.Vec2d(0, 0)

                    for point in contact_set.points:
                        if point.distance < -0.001:
                            push = contact_set.normal * (point.distance)
                            if push.length_squared > best_push.length_squared:
                                best_push = push

                    if best_push.length_squared > 0:
                        total_push += best_push
                        hits += 1

            if hits > 0:
                if total_push.length_squared < 0.000001:
                    break
                current_pos += total_push
            else:
                break

        phys.body.position = pos
        return current_pos

    def _get_poly_radius(self, shape: pymunk.Poly) -> float:
        if shape in self._poly_radius_cache:
            return self._poly_radius_cache[shape]

        verts = shape.get_vertices()
        sweep_origin_local = getattr(shape, "offset", pymunk.Vec2d(0, 0))

        max_sq = 0.0
        for v in verts:
            d_sq = (v - sweep_origin_local).length_squared
            if d_sq > max_sq:
                max_sq = d_sq

        radius = math.sqrt(max_sq)
        self._poly_radius_cache[shape] = radius
        return radius
