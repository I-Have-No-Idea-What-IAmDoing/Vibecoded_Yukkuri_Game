
import pygame
import math
from typing import List, Tuple, Dict

# Try to import numpy for fast gradient generation
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class SurfacePool:
    """
    Pool of reusable surfaces to eliminate allocation overhead.
    Surfaces are keyed by size and reused across frames.
    """
    
    def __init__(self, max_pool_size: int = 32):
        self._pool: Dict[Tuple[int, int], List[pygame.Surface]] = {}
        self._max_pool_size = max_pool_size
    
    def acquire(self, width: int, height: int) -> pygame.Surface:
        """Get a surface from the pool or create a new one."""
        key = (width, height)
        if key in self._pool and self._pool[key]:
            surf = self._pool[key].pop()
            # Clear the surface for reuse
            surf.fill((0, 0, 0, 0))
            return surf
        return pygame.Surface((width, height), pygame.SRCALPHA)
    
    def release(self, surf: pygame.Surface) -> None:
        """Return a surface to the pool for reuse."""
        key = surf.get_size()
        if key not in self._pool:
            self._pool[key] = []
        # Limit pool size to prevent memory bloat
        if len(self._pool[key]) < self._max_pool_size:
            self._pool[key].append(surf)


class SoftwareLightingEngine:
    """
    Optimized software lighting engine for Pygame.
    Handles lightmaps, shadow casting, and spatial partitioning.
    
    Performance optimizations:
    - NumPy-based gradient generation (when available)
    - Surface pooling to eliminate allocation overhead
    - Optimized shadow calculations with reduced Python overhead
    - Fast path for 1.0 scale (no transform needed)
    """

    def __init__(self, screen_size: Tuple[int, int], scale: float = 1.0):
        self.scale = scale
        self.native_size = screen_size
        self.lightmap_size = (int(screen_size[0] * scale), int(screen_size[1] * scale))
        
        # Surfaces
        self.lightmap = pygame.Surface(self.lightmap_size)
        
        # Spatial Grid
        self.cell_size = 100  # World units
        self.grid: Dict[Tuple[int, int], List[Tuple[tuple, list]]] = {}
        self.occluders = []
        
        # Caches
        self.light_texture_cache: Dict[tuple, pygame.Surface] = {}
        
        # Surface pool for light rendering surfaces
        self.surface_pool = SurfacePool()
        
    def resize(self, width: int, height: int):
        self.native_size = (width, height)
        self.lightmap_size = (int(width * self.scale), int(height * self.scale))
        self.lightmap = pygame.Surface(self.lightmap_size)
        
    def clear(self, ambient_color: Tuple[int, int, int]):
        # Fill lightmap with ambient
        self.lightmap.fill(ambient_color)
        self.occluders.clear()
        self.grid.clear()
        
    def add_occluder(self, aabb: Tuple[float, float, float, float], vertices: List[Tuple[float, float]]):
        """
        Registers an occluder and adds it to the spatial grid.
        aabb: (min_x, max_x, min_y, max_y)
        """
        self.occluders.append((aabb, vertices))
        
        min_x, max_x, min_y, max_y = aabb
        
        start_col = int(min_x // self.cell_size)
        end_col = int(max_x // self.cell_size)
        start_row = int(min_y // self.cell_size)
        end_row = int(max_y // self.cell_size)
        
        for col in range(start_col, end_col + 1):
            for row in range(start_row, end_row + 1):
                cell = (col, row)
                if cell not in self.grid:
                    self.grid[cell] = []
                self.grid[cell].append((aabb, vertices))

    def render_light(self, position: Tuple[float, float], radius: float, color: Tuple[int, int, int], intensity: float):
        """
        Renders a single light with shadows onto the lightmap.
        """
        lx, ly = position
        
        # Convert to lightmap space for rendering
        # Round to nearest integer to prevent sub-pixel jitter
        sx = int(lx * self.scale)
        sy = int(ly * self.scale)
        sr = radius * self.scale
        
        # Query Occluders
        relevant_occluders = self._query_grid(lx, ly, radius)
        
        # Render Light with Shadow Volumes
        self._draw_light_shadow_volume(sx, sy, sr, lx, ly, radius, color, intensity, relevant_occluders)

    def _draw_light_shadow_volume(self, sx: int, sy: int, sr: float, lx: float, ly: float, radius: float, color: Tuple[int, int, int], intensity: float, occluders: List):
        """
        Draws the light texture and applies subtractive shadow volumes.
        """
        sr_key = int(max(1, sr))
        surf_size = sr_key * 2
        
        # Sub-pixel offset for smooth light movement
        off_x = (lx * self.scale) - sx
        off_y = (ly * self.scale) - sy
        
        # Get Cached Gradient Texture
        grad_surf = self._get_gradient_surface(sr_key, color, intensity)
        
        # Acquire surface from pool instead of creating new one
        light_surf = self.surface_pool.acquire(surf_size, surf_size)
        
        # Blit the gradient with sub-pixel offset
        light_surf.blit(grad_surf, (off_x, off_y))
        
        # Draw Shadow Volumes (Subtractive)
        if occluders:
            if HAS_NUMPY:
                self._draw_shadow_volumes_numpy(light_surf, sr_key, lx, ly, sx, sy, radius, occluders)
            else:
                self._draw_shadow_volumes_optimized(light_surf, sr_key, lx, ly, sx, sy, radius, occluders)

        # Composite
        dest_rect = light_surf.get_rect(center=(sx, sy))
        self.lightmap.blit(light_surf, dest_rect, special_flags=pygame.BLEND_ADD)
        
        # Release surface back to pool
        self.surface_pool.release(light_surf)

    def _draw_shadow_volumes_optimized(self, light_surf: pygame.Surface, sr_key: int, lx: float, ly: float, sx: int, sy: int, radius: float, occluders: List):
        """
        Optimized shadow volume drawing with reduced Python overhead.
        Pre-computes common values and minimizes per-vertex calculations.
        """
        hx = sr_key
        hy = sr_key
        extrude_dist = radius * 2.0
        scale = self.scale
        
        # Pre-compute for coordinate transform
        sx_scaled = sx
        sy_scaled = sy
        
        for _, vertices in occluders:
            n = len(vertices)
            if n < 2:
                continue
                
            # Process all edges of this occluder
            for i in range(n):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % n]
                
                # Vector from light to vertices
                rel_x1 = p1[0] - lx
                rel_y1 = p1[1] - ly
                rel_x2 = p2[0] - lx
                rel_y2 = p2[1] - ly
                
                # Fast distance calculation (avoid math.hypot overhead)
                dist1_sq = rel_x1 * rel_x1 + rel_y1 * rel_y1
                dist2_sq = rel_x2 * rel_x2 + rel_y2 * rel_y2
                
                # Fast inverse sqrt approximation or regular sqrt
                if dist1_sq < 0.000001:
                    dist1_sq = 0.000001
                if dist2_sq < 0.000001:
                    dist2_sq = 0.000001
                    
                inv_dist1 = 1.0 / (dist1_sq ** 0.5)
                inv_dist2 = 1.0 / (dist2_sq ** 0.5)
                
                # Extrusion (Far points) - normalized direction * extrude distance
                ex1_x = rel_x1 * inv_dist1 * extrude_dist
                ex1_y = rel_y1 * inv_dist1 * extrude_dist
                ex2_x = rel_x2 * inv_dist2 * extrude_dist
                ex2_y = rel_y2 * inv_dist2 * extrude_dist
                
                # Construct Quad in world space, then transform to local
                # World quad: p1, p2, p2+extrusion, p1+extrusion
                # Transform: (world * scale - screen_pos) + half_size
                
                # Inline coordinate transform for speed
                q0_x = (p1[0] * scale - sx_scaled) + hx
                q0_y = (p1[1] * scale - sy_scaled) + hy
                q1_x = (p2[0] * scale - sx_scaled) + hx
                q1_y = (p2[1] * scale - sy_scaled) + hy
                q2_x = ((p2[0] + ex2_x) * scale - sx_scaled) + hx
                q2_y = ((p2[1] + ex2_y) * scale - sy_scaled) + hy
                q3_x = ((p1[0] + ex1_x) * scale - sx_scaled) + hx
                q3_y = ((p1[1] + ex1_y) * scale - sy_scaled) + hy
                
                # Draw opaque black to erase light
                pygame.draw.polygon(light_surf, (0, 0, 0, 255), [
                    (q0_x, q0_y), (q1_x, q1_y), (q2_x, q2_y), (q3_x, q3_y)
                ])

    def _draw_shadow_volumes_numpy(self, light_surf: pygame.Surface, sr_key: int, lx: float, ly: float, sx: int, sy: int, radius: float, occluders: List):
        """
        NumPy-accelerated shadow volume drawing.
        Processes all edges of each occluder using vectorized operations.
        """
        hx = sr_key
        hy = sr_key
        extrude_dist = radius * 2.0
        scale = self.scale
        sx_scaled = sx
        sy_scaled = sy
        
        for _, vertices in occluders:
            n = len(vertices)
            if n < 2:
                continue
            
            # Convert vertices to numpy array once
            verts = np.array(vertices, dtype=np.float64)
            
            # Create arrays for p1 (current) and p2 (next) vertices
            p1 = verts
            p2 = np.roll(verts, -1, axis=0)
            
            # Vector from light to vertices
            rel1 = p1 - np.array([lx, ly])
            rel2 = p2 - np.array([lx, ly])
            
            # Calculate distances (avoid zero division)
            dist1_sq = np.sum(rel1 * rel1, axis=1)
            dist2_sq = np.sum(rel2 * rel2, axis=1)
            dist1_sq = np.maximum(dist1_sq, 0.000001)
            dist2_sq = np.maximum(dist2_sq, 0.000001)
            
            inv_dist1 = 1.0 / np.sqrt(dist1_sq)
            inv_dist2 = 1.0 / np.sqrt(dist2_sq)
            
            # Extrusion vectors (normalized direction * extrude distance)
            ex1 = rel1 * (inv_dist1 * extrude_dist)[:, np.newaxis]
            ex2 = rel2 * (inv_dist2 * extrude_dist)[:, np.newaxis]
            
            # Calculate quad corners in local surface space
            # q0 = p1, q1 = p2, q2 = p2 + ex2, q3 = p1 + ex1
            # Transform: (world * scale - screen_pos) + half_size
            q0 = (p1 * scale - np.array([sx_scaled, sy_scaled])) + np.array([hx, hy])
            q1 = (p2 * scale - np.array([sx_scaled, sy_scaled])) + np.array([hx, hy])
            q2 = ((p2 + ex2) * scale - np.array([sx_scaled, sy_scaled])) + np.array([hx, hy])
            q3 = ((p1 + ex1) * scale - np.array([sx_scaled, sy_scaled])) + np.array([hx, hy])
            
            # Draw each shadow quad
            for i in range(n):
                pygame.draw.polygon(light_surf, (0, 0, 0, 255), [
                    (q0[i, 0], q0[i, 1]),
                    (q1[i, 0], q1[i, 1]),
                    (q2[i, 0], q2[i, 1]),
                    (q3[i, 0], q3[i, 1])
                ])

    def _get_gradient_surface(self, radius: int, color: Tuple[int, int, int], intensity: float) -> pygame.Surface:
        """
        Generates (or retrieves) a high-quality radial gradient surface.
        Uses NumPy for fast generation when available.
        """
        int_c = (int(color[0]), int(color[1]), int(color[2]))
        key = (radius, int_c, int(intensity * 100))
        
        if key in self.light_texture_cache:
            return self.light_texture_cache[key]
        
        if HAS_NUMPY:
            surf = self._generate_gradient_numpy(radius, int_c, intensity)
        else:
            surf = self._generate_gradient_pygame(radius, int_c, intensity)
            
        self.light_texture_cache[key] = surf
        return surf

    def _generate_gradient_numpy(self, radius: int, color: Tuple[int, int, int], intensity: float) -> pygame.Surface:
        """
        Fast NumPy-based gradient generation.
        Creates the gradient in a single vectorized operation.
        
        For BLEND_ADD, we need to vary the RGB values directly, not alpha,
        since additive blending adds RGB without scaling by alpha.
        """
        size = radius * 2
        if size < 1:
            size = 1
        
        # Create coordinate grids centered at (radius, radius)
        x = np.arange(size, dtype=np.float32) - radius + 0.5
        y = np.arange(size, dtype=np.float32) - radius + 0.5
        xx, yy = np.meshgrid(x, y)
        
        # Calculate distance from center for each pixel (normalized 0-1)
        dist = np.sqrt(xx * xx + yy * yy) / max(radius, 1)
        
        # Quadratic falloff: (1 - dist)^2, clamped to 0-1
        falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2
        
        # Scale falloff by intensity
        falloff = falloff * intensity
        
        # Calculate RGB channels (vary intensity, not alpha)
        r = (falloff * color[0]).astype(np.uint8)
        g = (falloff * color[1]).astype(np.uint8)
        b = (falloff * color[2]).astype(np.uint8)
        
        # Create RGB surface (no alpha needed for additive blending)
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))  # Start with black
        
        # Use surfarray to set pixel data
        # surfarray expects (width, height, 3) = (x, y, rgb), so transpose
        pixels = pygame.surfarray.pixels3d(surf)
        pixels[:, :, 0] = r.T
        pixels[:, :, 1] = g.T
        pixels[:, :, 2] = b.T
        del pixels  # Release the surface lock
        
        return surf

    def _generate_gradient_pygame(self, radius: int, color: Tuple[int, int, int], intensity: float) -> pygame.Surface:
        """
        Fallback gradient generation using pygame.draw.circle.
        Optimized with larger step size for acceptable quality.
        """
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = (radius, radius)
        
        base_alpha = max(0, min(255, int(255 * intensity)))
        
        # Use step of 2 for better performance while maintaining quality
        steps = max(1, radius // 2)
        
        for i in range(steps):
            # Calculate radius for this ring
            t = i / float(steps)
            r = int(radius * (1.0 - t))
            if r <= 0:
                continue
            
            # Falloff calculation
            fn = t  # 0 at edge, 1 at center
            alpha_val = int(base_alpha * (fn ** 2))
            
            # Draw ring with width 3 to cover gaps from larger step size
            pygame.draw.circle(surf, color + (alpha_val,), center, r, width=3)
        
        # Fill center
        pygame.draw.circle(surf, color + (base_alpha,), center, 3)
        
        return surf

    def get_surface(self) -> pygame.Surface:
        """
        Returns the final lightmap.
        Fast path: skip transform if scale is 1.0 (native resolution).
        """
        # Fast path - no scaling needed
        if self.scale == 1.0:
            return self.lightmap
            
        return pygame.transform.smoothscale(self.lightmap, self.native_size)

    def _query_grid(self, lx: float, ly: float, radius: float) -> List[Tuple[tuple, list]]:
        """
        Returns a list of occluders (aabb, vertices) that overlap the light's bounding box.
        """
        candidates = []
        seen = set()
        
        min_x = lx - radius
        max_x = lx + radius
        min_y = ly - radius
        max_y = ly + radius
        
        cell_size = self.cell_size
        start_col = int(min_x // cell_size)
        end_col = int(max_x // cell_size)
        start_row = int(min_y // cell_size)
        end_row = int(max_y // cell_size)
        
        grid = self.grid
        
        for col in range(start_col, end_col + 1):
            for row in range(start_row, end_row + 1):
                cell = (col, row)
                if cell in grid:
                    for occluder in grid[cell]:
                        occ_id = id(occluder)
                        if occ_id not in seen:
                            # AABB Refined Check
                            aabb = occluder[0]
                            omi_x, oma_x, omi_y, oma_y = aabb
                            
                            if not (oma_x < min_x or omi_x > max_x or oma_y < min_y or omi_y > max_y):
                                candidates.append(occluder)
                                seen.add(occ_id)
        return candidates
