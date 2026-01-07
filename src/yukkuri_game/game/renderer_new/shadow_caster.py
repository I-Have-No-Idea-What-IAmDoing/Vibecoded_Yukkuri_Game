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
        occluders: List[List[Tuple[float, float]]]
    ) -> List[Tuple[float, float]]:
        """
        Calculates the visibility polygon for a light source.

        Args:
            light_pos: (x, y) of the light.
            radius: Maximum radius of the light.
            occluders: List of polygons, where each polygon is a list of (x, y) vertices.

        Returns:
            A list of (x, y) points defining the visibility polygon.
        """
        lx, ly = light_pos

        # Define light bounds (Square approximation for ray targets)
        # We use a square bounding box for the light radius to cast rays at corners.
        # But for actual intersection, we might want to clip to radius later.
        # For simplicity, we treat the "world" as the light radius box for this calculation.

        r = radius
        bounds_poly = [
            (lx - r, ly - r),
            (lx + r, ly - r),
            (lx + r, ly + r),
            (lx - r, ly + r)
        ]

        # 1. Collect segments
        segments = []
        unique_points = set()

        # Add boundary segments
        for i in range(4):
            p1 = bounds_poly[i]
            p2 = bounds_poly[(i + 1) % 4]
            segments.append((p1, p2))
            unique_points.add(p1)

        # Bounds for culling
        min_x, max_x = lx - r, lx + r
        min_y, max_y = ly - r, ly + r

        for poly in occluders:
            # Simple AABB check for the whole polygon
            p_min_x = min(p[0] for p in poly)
            p_max_x = max(p[0] for p in poly)
            p_min_y = min(p[1] for p in poly)
            p_max_y = max(p[1] for p in poly)

            if (p_max_x < min_x or p_min_x > max_x or
                p_max_y < min_y or p_min_y > max_y):
                continue

            for i in range(len(poly)):
                p1 = poly[i]
                p2 = poly[(i + 1) % len(poly)]
                segments.append((p1, p2))
                unique_points.add(p1)
                unique_points.add(p2)

        # 2. Generate angles
        angles = []
        for p in unique_points:
            dx = p[0] - lx
            dy = p[1] - ly
            angle = math.atan2(dy, dx)
            # Add epsilon rays to hit slightly to the left/right of vertices
            angles.append(angle - 0.0001)
            angles.append(angle)
            angles.append(angle + 0.0001)

        # Sort angles
        angles.sort()

        # 3. Cast rays
        polygon_points = []

        for angle in angles:
            dx = math.cos(angle)
            dy = math.sin(angle)

            # Max ray length (diagonal of square is r * sqrt(2), using r*2 is safe)
            max_dist = r * 2.0

            closest_dist = max_dist
            closest_pt = (lx + dx * max_dist, ly + dy * max_dist)

            # Check against all segments
            for sp1, sp2 in segments:
                # Intersection logic
                pt, dist = self._get_intersection(lx, ly, dx, dy, sp1, sp2)
                if pt and dist < closest_dist:
                    closest_dist = dist
                    closest_pt = pt

            # Filter close points (duplicates) to clean up polygon?
            # Not strictly necessary but good for rendering.
            if not polygon_points or \
               abs(polygon_points[-1][0] - closest_pt[0]) > 0.1 or \
               abs(polygon_points[-1][1] - closest_pt[1]) > 0.1:
                polygon_points.append(closest_pt)

        return polygon_points

    def _get_intersection(
        self,
        lx: float, ly: float, dx: float, dy: float,
        sp1: Tuple[float, float], sp2: Tuple[float, float]
    ) -> Tuple[Optional[Tuple[float, float]], float]:
        """
        Finds intersection between ray (lx,ly) -> (dx,dy) and segment sp1-sp2.
        Returns (point, distance) or (None, infinity).
        """
        # Ray: P = L + t * D
        # Segment: P = S1 + u * (S2 - S1)

        sx1, sy1 = sp1
        sx2, sy2 = sp2

        sdx = sx2 - sx1
        sdy = sy2 - sy1

        # Cross product of directions
        det = dx * sdy - dy * sdx

        if abs(det) < 0.000001:
            return None, float('inf')

        diff_x = sx1 - lx
        diff_y = sy1 - ly

        u = (diff_x * dy - diff_y * dx) / det
        if u < 0 or u > 1:
            return None, float('inf')

        t = (diff_x * sdy - diff_y * sdx) / det
        if t < 0:
            return None, float('inf')

        # Point
        px = lx + t * dx
        py = ly + t * dy
        return (px, py), t
