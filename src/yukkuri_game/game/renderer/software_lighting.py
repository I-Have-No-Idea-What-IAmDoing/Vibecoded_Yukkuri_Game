
import pygame
import math
import random
from typing import List, Tuple, Optional, Dict

class SoftwareLightingEngine:
    """
    Optimized software lighting engine for Pygame.
    Handles lightmaps, shadow casting, and spatial partitioning.
    """

    def __init__(self, screen_size: Tuple[int, int], scale: float = 1.0):
        self.scale = scale
        self.native_size = screen_size
        self.lightmap_size = (int(screen_size[0] * scale), int(screen_size[1] * scale))
        
        # Surfaces
        self.lightmap = pygame.Surface(self.lightmap_size)
        self.temp_surface = None # Created on demand
        
        # Spatial Grid
        self.cell_size = 100 # World units
        self.grid: Dict[Tuple[int, int], List[Tuple[tuple, list]]] = {} 
        self.occluders = []
        
        # Caches
        self.light_texture_cache = {}
        
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
        
        # 1. Cull check (basic screen bounds)
        # Convert to lightmap space for rendering
        # Round to nearest integer to prevent sub-pixel jitter during shadow drawing vs blitting
        sx = int(lx * self.scale)
        sy = int(ly * self.scale)
        sr = radius * self.scale
        

        
        # 2. Query Occluders
        relevant_occluders = self._query_grid(lx, ly, radius)
        
        # 3. Render Light with Shadow Volumes
        self._draw_light_shadow_volume(sx, sy, sr, lx, ly, radius, color, intensity, relevant_occluders)

    def _draw_light_shadow_volume(self, sx: int, sy: int, sr: float, lx: float, ly: float, radius: float, color: Tuple[int, int, int], intensity: float, occluders: List):
        """
        Draws the light texture and applies subtractive shadow volumes.
        """
        sr_key = int(max(1, sr))
        
        # Sub-pixel offset for smooth light movement
        off_x = (lx * self.scale) - sx
        off_y = (ly * self.scale) - sy
        
        # 1. Get Cached Gradient Texture
        # We cache the gradient centered perfectly. We effectively "move" the light 
        # by blitting it at a sub-pixel offset into the render surface.
        grad_surf = self._get_gradient_surface(sr_key, color, intensity)
        
        # Create render surface
        # Optimization: Could reuse a pool, but surface creation is relatively cheap compared to the gradient drawing was.
        light_surf = pygame.Surface((sr_key * 2, sr_key * 2), pygame.SRCALPHA)
        
        # Blit the gradient with sub-pixel offset
        # This keeps the "glow" smooth while the surface remains snapped to the integer grid
        light_surf.blit(grad_surf, (off_x, off_y))
        
        # 2. Draw Shadow Volumes (Subtractive)
        if occluders:
            hx = sr_key
            hy = sr_key
            extrude_dist = radius * 2.0 
            
            # Bias to pull shadow start slightly towards light to prevent gaps/leaks
            # at wall edges due to resolution/rounding.
            # With Native Resolution (1.0) and Integer Snapping, any bias > 0 creates visible
            # "peter panning" artifacts (shadows starting in thin air).
            # We set it to 0.0 as precision should be sufficient now.
            origin_bias = 0.0 
            
            for _, vertices in occluders:
                n = len(vertices)
                for i in range(n):
                    p1 = vertices[i]
                    p2 = vertices[(i + 1) % n]
                    
                    # Compute vector from Light to P1
                    rel_x1 = p1[0] - lx
                    rel_y1 = p1[1] - ly
                    dist1 = math.hypot(rel_x1, rel_y1)
                    if dist1 < 0.001: dist1 = 0.001
                    
                    # Compute vector from Light to P2
                    rel_x2 = p2[0] - lx
                    rel_y2 = p2[1] - ly
                    dist2 = math.hypot(rel_x2, rel_y2)
                    if dist2 < 0.001: dist2 = 0.001

                    # Extrusion (Far points)
                    ex1_x = (rel_x1 / dist1) * extrude_dist
                    ex1_y = (rel_y1 / dist1) * extrude_dist
                    
                    ex2_x = (rel_x2 / dist2) * extrude_dist
                    ex2_y = (rel_y2 / dist2) * extrude_dist
                    
                    # Bias (Near points - shifted towards light)
                    bias_x1 = (rel_x1 / dist1) * origin_bias
                    bias_y1 = (rel_y1 / dist1) * origin_bias
                    
                    bias_x2 = (rel_x2 / dist2) * origin_bias
                    bias_y2 = (rel_y2 / dist2) * origin_bias
                    
                    p1_bias = (p1[0] - bias_x1, p1[1] - bias_y1)
                    p2_bias = (p2[0] - bias_x2, p2[1] - bias_y2)
                    
                    # Construct Quad
                    world_quad = [
                        p1_bias,
                        p2_bias,
                        (p2[0] + ex2_x, p2[1] + ex2_y),
                        (p1[0] + ex1_x, p1[1] + ex1_y)
                    ]
                    
                    # Transform to Local coords
                    local_quad = []
                    for wx, wy in world_quad:
                        swx = wx * self.scale
                        swy = wy * self.scale
                        local_quad.append(((swx - sx) + hx, (swy - sy) + hy))
                    
                    # Draw Opaque Black to "Erase" light
                    pygame.draw.polygon(light_surf, (0, 0, 0, 255), local_quad)

        # 3. Composite
        dest_rect = light_surf.get_rect(center=(sx, sy))
        self.lightmap.blit(light_surf, dest_rect, special_flags=pygame.BLEND_ADD)

    def _get_gradient_surface(self, radius: int, color: Tuple[int, int, int], intensity: float) -> pygame.Surface:
        """
        Generates (or retrieves) a high-quality radial gradient surface.
        """
        int_c = (int(color[0]), int(color[1]), int(color[2]))
        key = (radius, int_c, int(intensity * 100))
        
        if key in self.light_texture_cache:
            return self.light_texture_cache[key]
            
        # Create new gradient surface at full resolution
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = (radius, radius)
        
        base_alpha = max(0, min(255, int(255 * intensity)))
        
        # WE use a per-pixel-radius loop (rings)
        # This gives perfect smoothness without accumulation artifacts.
        steps = int(radius)
        if steps < 1: steps = 1
        
        for i in range(steps):
            # i goes from 0 (outermost) to radius-1 (innermost)
            # t goes from 0.0 to 1.0
            t = i / float(steps)
            
            # Radius shrinks
            r = radius - i
            if r <= 0: continue
            
            # Normalized distance from center (0.0 = center, 1.0 = edge)
            dist_norm = r / float(radius)
            
            # Quadratic falloff: alpha is high at center, 0 at edge
            scale = (1.0 - dist_norm) ** 2
            
            # Inverse: we want alpha to be high when r is small?
            # No, wait.
            # dist_norm=1 (edge) -> scale=0 -> alpha=0.
            # dist_norm=0 (center) -> scale=1 -> alpha=base.
            # Wait, 1.0 - dist_norm IS the closeness to center.
            # So (1.0 - dist_norm) goes from 0 (edge) to 1 (center).
            
            # Let's check 't'. t=0 (Outer). r=radius. dist_norm=1. scale=0.
            # t=1 (Inner). r=0. dist_norm=0. scale=1.
            
            # Actually, let's use a simpler logic for visual quality.
            # The previous one used (1-t)^2 where t=0 was center?
            # No, let's stick to the physical logic:
            # Brightness falls off with distance.
            
            # Logic:
            fn = 1.0 - (r / radius) # 0 at edge, 1 at center
            alpha_val = int(base_alpha * (fn ** 2))
            
            # Draw ring of width 2 to ensure no gaps between 1px steps due to aliasing
            # width=2 guarantees overlap, which is fine as long as we draw enough steps
            pygame.draw.circle(surf, int_c + (alpha_val,), center, r, width=2)
            
        # Fill center dot to prevent hole
        pygame.draw.circle(surf, int_c + (255,), center, 2)
        
        self.light_texture_cache[key] = surf
        return surf

    def get_surface(self) -> pygame.Surface:
        """
        Returns the final upscaled lightmap.
        """
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
        
        start_col = int(min_x // self.cell_size)
        end_col = int(max_x // self.cell_size)
        start_row = int(min_y // self.cell_size)
        end_row = int(max_y // self.cell_size)
        
        for col in range(start_col, end_col + 1):
            for row in range(start_row, end_row + 1):
                cell = (col, row)
                if cell in self.grid:
                    for occluder in self.grid[cell]:
                        occ_id = id(occluder) # Simple unique check
                        if occ_id not in seen:
                            # AABB Refined Check
                            oma_x = occluder[0][1]
                            omi_x = occluder[0][0]
                            oma_y = occluder[0][3]
                            omi_y = occluder[0][2]
                            
                            if not (oma_x < min_x or omi_x > max_x or oma_y < min_y or omi_y > max_y):
                                candidates.append(occluder)
                                seen.add(occ_id)
        return candidates


