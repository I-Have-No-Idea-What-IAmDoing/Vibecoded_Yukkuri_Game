import math
from typing import List, Tuple


class ShadowCaster:
    """
    Calculates 2D visibility polygons for point lights.
    """

    def __init__(self) -> None:
        pass

    def calculate_visibility_polygon(
        self,
        light_pos: Tuple[float, float],
        radius: float,
        occluders: List[
            Tuple[Tuple[float, float, float, float], List[Tuple[float, float]]]
        ],
    ) -> List[Tuple[float, float]]:
        """
        Calculates the visibility polygon for a light source.

        Args:
            light_pos: (x, y) of the light.
            radius: Maximum radius of the light.
            occluders: List of ((min_x, max_x, min_y, max_y), vertices).

        Returns:
            A list of (x, y) points defining the visibility polygon.
        """
        lx, ly = light_pos
        r = radius

        # Bounds for culling (Square approximation)
        min_x, max_x = lx - r, lx + r
        min_y, max_y = ly - r, ly + r

        # 1. Collect segments from relevant occluders
        # We also collect unique points for ray casting
        segments = []
        unique_points = []

        # Add boundary segments (The "World Box" for the light)
        bounds_poly = [
            (lx - r, ly - r),
            (lx + r, ly - r),
            (lx + r, ly + r),
            (lx - r, ly + r),
        ]

        # Add bounds segments
        for i in range(4):
            p1 = bounds_poly[i]
            p2 = bounds_poly[(i + 1) % 4]
            segments.append((p1, p2))
            unique_points.append(p1)

        # Filter occluders using pre-calculated AABB
        for (omin_x, omax_x, omin_y, omax_y), poly in occluders:
            # AABB Overlap Check
            if omax_x < min_x or omin_x > max_x or omax_y < min_y or omin_y > max_y:
                continue

            p_len = len(poly)
            for i in range(p_len):
                p1 = poly[i]
                p2 = poly[(i + 1) % p_len]
                segments.append((p1, p2))
                unique_points.append(p1)
                unique_points.append(p2)

        # Optimization: Only add unique points (corners)
        points_set = set(unique_points)

        # 2. Generate rays/angles
        # Optimization: Only cast 2 rays per vertex (epsilon offset)
        angles = []
        epsilon = 0.0001

        for p in points_set:
            dx = p[0] - lx
            dy = p[1] - ly
            angle = math.atan2(dy, dx)
            angles.append(angle - epsilon)
            angles.append(angle + epsilon)

        angles.sort()

        # 3. Pre-process segments relative to light to avoid re-calculation in inner loop
        # We store: (rel_x1, rel_y1, sdx, sdy)
        optimized_segments = []
        for (sx1, sy1), (sx2, sy2) in segments:
            optimized_segments.append((sx1 - lx, sy1 - ly, sx2 - sx1, sy2 - sy1))

        # 4. Cast rays
        polygon_points = []
        prev_pt = None

        # Safe max distance
        max_dist = r * 2.0

        for angle in angles:
            dx = math.cos(angle)
            dy = math.sin(angle)

            # We want smallest positive t.
            closest_t = max_dist

            # Intersection Check
            # We avoid division where possible.
            # Using Cramer's rule adaptation and checking inequalities before division.

            for rx, ry, sdx, sdy in optimized_segments:
                det = dx * sdy - dy * sdx

                # Check 1: Parallel
                if -1e-6 < det < 1e-6:
                    continue

                # Check 2: u must be in [0, 1]
                # u = u_num / det
                u_num = rx * dy - ry * dx

                # If det > 0: 0 <= u_num <= det
                # If det < 0: det <= u_num <= 0
                if det > 0:
                    if u_num < 0 or u_num > det:
                        continue
                else:
                    if u_num > 0 or u_num < det:
                        continue

                # Check 3: t must be > 0 and < closest_t
                # t = t_num / det
                t_num = rx * sdy - ry * sdx

                if det > 0:
                    if t_num <= 0 or t_num >= closest_t * det:
                        continue
                else:
                    if t_num >= 0 or t_num <= closest_t * det:
                        continue

                # If we passed checks, this is the new closest
                closest_t = t_num / det

            # Reconstruct point
            closest_pt = (lx + dx * closest_t, ly + dy * closest_t)

            # Filter close points to simplify polygon
            if (
                prev_pt
                and abs(prev_pt[0] - closest_pt[0]) < 0.1
                and abs(prev_pt[1] - closest_pt[1]) < 0.1
            ):
                continue

            polygon_points.append(closest_pt)
            prev_pt = closest_pt

        return polygon_points
