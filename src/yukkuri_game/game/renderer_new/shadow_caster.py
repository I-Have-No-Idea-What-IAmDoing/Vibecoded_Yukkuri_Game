import math
from typing import List, Tuple, Optional

class ShadowCaster:
    """
    Calculates 2D visibility polygons for point lights.
    """

    def __init__(self):
        pass

    def calculate_visibility_polygon(
        self,
        light_pos: Tuple[float, float],
        radius: float,
        occluders: List[Tuple[Tuple[float, float, float, float], List[Tuple[float, float]]]]
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
        segments = []
        unique_points = []

        # Add boundary segments (The "World Box" for the light)
        bounds_poly = [
            (lx - r, ly - r),
            (lx + r, ly - r),
            (lx + r, ly + r),
            (lx - r, ly + r)
        ]

        for i in range(4):
            p1 = bounds_poly[i]
            p2 = bounds_poly[(i + 1) % 4]
            segments.append((p1, p2))
            unique_points.append(p1)

        # Filter occluders using pre-calculated AABB
        for (omin_x, omax_x, omin_y, omax_y), poly in occluders:
            # AABB Overlap Check
            if (omax_x < min_x or omin_x > max_x or
                omax_y < min_y or omin_y > max_y):
                continue

            p_len = len(poly)
            for i in range(p_len):
                p1 = poly[i]
                p2 = poly[(i + 1) % p_len]
                segments.append((p1, p2))
                unique_points.append(p1)
                unique_points.append(p2)

        # 2. Generate rays/angles
        # Optimization: Only cast 2 rays per vertex (epsilon offset)
        # Using a small epsilon for angle offset
        angles = []
        epsilon = 0.0001

        for p in unique_points:
            dx = p[0] - lx
            dy = p[1] - ly
            angle = math.atan2(dy, dx)
            angles.append(angle - epsilon)
            angles.append(angle + epsilon)

        angles.sort()

        # 3. Cast rays
        polygon_points = []
        max_dist = r * 2.0  # Safe max distance

        # Pre-calculate segment data to avoid re-accessing tuples in tight loop
        # layout: (x1, y1, dx, dy) where dx, dy is vector P2-P1
        # This helps _get_intersection avoid subtractions
        optimized_segments = []
        for (sx1, sy1), (sx2, sy2) in segments:
            optimized_segments.append((sx1, sy1, sx2 - sx1, sy2 - sy1))

        prev_pt = None

        for angle in angles:
            dx = math.cos(angle)
            dy = math.sin(angle)

            closest_t = max_dist # t is distance here since direction is normalized

            # Intersection Check
            # Inline the intersection logic for speed
            for sx1, sy1, sdx, sdy in optimized_segments:

                # Cross product of ray dir (dx, dy) and seg dir (sdx, sdy)
                det = dx * sdy - dy * sdx

                if abs(det) < 0.000001:
                    continue

                diff_x = sx1 - lx
                diff_y = sy1 - ly

                # u = ((S1 - L) x D) / det
                u = (diff_x * dy - diff_y * dx) / det

                if u < 0 or u > 1:
                    continue

                # t = ((S1 - L) x (S2 - S1)) / det
                t = (diff_x * sdy - diff_y * sdx) / det

                if t > 0 and t < closest_t:
                    closest_t = t

            # Reconstruct point
            closest_pt = (lx + dx * closest_t, ly + dy * closest_t)

            # Filter close points
            if prev_pt and abs(prev_pt[0] - closest_pt[0]) < 0.1 and abs(prev_pt[1] - closest_pt[1]) < 0.1:
                continue

            polygon_points.append(closest_pt)
            prev_pt = closest_pt

        return polygon_points
