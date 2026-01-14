import pygame

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
        self._pool: dict[tuple[int, int], list[pygame.Surface]] = {}
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

    def __init__(self, screen_size: tuple[int, int], scale: float = 1.0):
        self.scale = scale
        self.native_size = screen_size
        self.lightmap_size = (int(screen_size[0] * scale), int(screen_size[1] * scale))

        # Surfaces
        self.lightmap = pygame.Surface(self.lightmap_size)

        # Spatial Grid
        self.cell_size = 100  # World units
        self.grid: dict[
            tuple[int, int],
            list[tuple[tuple[float, float, float, float], list[tuple[float, float]]]],
        ] = {}
        self.occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ] = []

        # Caches
        self.light_texture_cache: dict[
            tuple[int, tuple[int, int, int], int], pygame.Surface
        ] = {}

        # Static light cache: entity_id -> (light_surface, cache_key)
        # Cache key includes params that would invalidate the cache
        self.static_light_cache: dict[
            int, tuple[pygame.Surface, tuple[int, tuple[int, int, int], int, bool]]
        ] = {}

        # Surface pool for light rendering surfaces
        self.surface_pool = SurfacePool()

        self.debug: bool = False

    def toggle_debug(self, enabled: bool) -> None:
        self.debug = enabled

    def resize(self, width: int, height: int) -> None:
        self.native_size = (width, height)
        self.lightmap = pygame.Surface(
            (int(width * self.scale), int(height * self.scale))
        )

    def clear(self, ambient_color: tuple[int, int, int]) -> None:
        # Fill lightmap with ambient
        self.lightmap.fill(ambient_color)
        self.occluders.clear()
        self.grid.clear()

    def add_occluder(
        self,
        aabb: tuple[float, float, float, float],
        vertices: list[tuple[float, float]],
    ) -> None:
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

    def render_light(
        self,
        position: tuple[float, float],
        radius: float,
        color: tuple[int, int, int],
        intensity: float,
        soft_shadows: bool = True,
        static: bool = False,
        entity_id: int = -1,
    ) -> None:
        """
        Renders a single light with shadows onto the lightmap.

        Args:
            position: Light position in screen space.
            radius: Light radius.
            color: Light color (RGB).
            intensity: Light intensity multiplier.
            soft_shadows: If True, blur shadow edges for a softer look.
            static: If True, cache the light+shadow surface for reuse.
            entity_id: Unique ID for caching static lights.
        """
        lx, ly = position

        # Convert to lightmap space for rendering
        # Round to nearest integer to prevent sub-pixel jitter
        sx = int(lx * self.scale)
        sy = int(ly * self.scale)
        sr = radius * self.scale

        # Quantize radius for large lights to prevent cache thrashing
        if sr > 500:
            sr = round(sr / 50.0) * 50.0
        elif sr > 100:
            sr = round(sr / 10.0) * 10.0

        sr_key = int(max(1, sr))

        # Viewport Culling / Clipping
        # Light bounds in screen space
        light_rect = pygame.Rect(sx - sr, sy - sr, sr * 2, sr * 2)
        screen_rect = self.lightmap.get_rect()

        # Clipped visible rect
        clip_rect = light_rect.clip(screen_rect)

        if clip_rect.width <= 0 or clip_rect.height <= 0:
            return

        # Static light caching: check if we have a valid cached surface
        if static and entity_id >= 0:
            cache_key = (sr_key, color, int(intensity * 100), soft_shadows)
            if entity_id in self.static_light_cache:
                cached_surf, cached_key = self.static_light_cache[entity_id]
                if cached_key == cache_key:
                    # Cache hit! Just blit the cached surface at current position
                    dest_rect = cached_surf.get_rect(center=(sx, sy))
                    self.lightmap.blit(
                        cached_surf, dest_rect, special_flags=pygame.BLEND_ADD
                    )
                    return

        # Query Occluders
        relevant_occluders = self._query_grid(lx, ly, radius)

        # Render Light with Shadow Volumes (Clipped)
        light_surf = self._draw_light_shadow_volume(
            clip_rect,
            sr_key,
            lx,
            ly,
            radius,
            color,
            intensity,
            relevant_occluders,
            soft_shadows,
        )

        # Cache the result for static lights
        if static and entity_id >= 0 and light_surf is not None:
            cache_key = (sr_key, color, int(intensity * 100), soft_shadows)
            # Make a copy for the cache (the original goes back to the pool)
            cached_copy = light_surf.copy()
            self.static_light_cache[entity_id] = (cached_copy, cache_key)

    def _draw_light_shadow_volume(
        self,
        clip_rect: pygame.Rect,
        sr_key: int,
        lx: float,
        ly: float,
        radius: float,
        color: tuple[int, int, int],
        intensity: float,
        occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ],
        soft_shadows: bool = True,
    ) -> pygame.Surface:
        """
        Draws the light texture and applies subtractive shadow volumes.
        Supports soft shadows via low-res blur.
        Returns the rendered light surface for potential caching.
        """
        # Surface size is determined by the clipped area
        surf_w, surf_h = clip_rect.size

        # Calculate offsets for drawing relative to the clipped surface
        # clip_rect.x is the screen coordinate of the left edge of this surface.
        # We want to transform World -> Screen -> Surface
        # Screen = World * scale + camera_offset (already handled by lx, ly passed in?)
        # Wait, lx, ly are SCREEN coordinates of the light center.

        # The light center in Screen coords is (int(lx * scale), int(ly * scale)) which is roughly passed sx, sy
        # Note: We calculated sx, sy before quantization. But we need accurate center for shadows.
        sx_center = lx * self.scale
        sy_center = ly * self.scale

        # Surface Origin in Screen coords = clip_rect.topleft
        # So coordinate (x, y) on surface = Screen(x + clip_rect.x, y + clip_rect.y)

        # To draw the gradient correctly:
        # The gradient is a (sr*2, sr*2) image centered at (sr, sr).
        # In screen space, it is centered at (sx, sy).
        # TopLeft of gradient in Screen Space = (sx - sr, sy - sr).

        # We want to blit the part of the gradient that overlaps clip_rect.
        # Gradient Subsurface Rect (relative to gradient topleft):
        # x = clip_rect.x - (sx - sr)
        # y = clip_rect.y - (sy - sr)
        # w, h = clip_rect.size

        gx = clip_rect.x - (int(sx_center) - sr_key)
        gy = clip_rect.y - (int(sy_center) - sr_key)

        # Offset for shadow calculations
        # Shadow vertices calc: (World * scale - ScreenCenter) + HalfSize
        # Here we map directly to Surface.
        # Screen point P -> Surface point P' = P - clip_rect.topleft

        # Pass offset to shadow functions
        offset_x = clip_rect.x
        offset_y = clip_rect.y

        # Acquire surface from pool instead of creating new one
        light_surf = self.surface_pool.acquire(surf_w, surf_h)

        # Optimization: For huge lights, render gradient directly to clipped surface
        # entirely bypassing the allocation of a huge cached texture.
        if sr_key > 500:
            # Calculate light center relative to this surface
            cx = (lx * self.scale) - clip_rect.x
            cy = (ly * self.scale) - clip_rect.y
            self._render_gradient_direct(light_surf, cx, cy, radius, color, intensity)
        else:
            # Get Cached Gradient Texture
            grad_surf = self._get_gradient_surface(sr_key, color, intensity)

            # Blit the relevant chunk of the gradient
            grad_rect = grad_surf.get_rect()
            sub_rect = pygame.Rect(gx, gy, surf_w, surf_h)

            light_surf.blit(grad_surf, (0, 0), area=sub_rect)

        # Draw Shadow Volumes (Subtractive)
        if occluders:
            # Optimization: Skip soft shadows for huge lights (expensive blur)
            # Hard shadows are acceptable when zoomed in close
            use_soft = soft_shadows and sr_key <= 400

            if use_soft:
                self._draw_soft_shadows(
                    light_surf, sr_key, lx, ly, offset_x, offset_y, radius, occluders
                )
            elif HAS_NUMPY:
                self._draw_shadow_volumes_numpy(
                    light_surf, sr_key, lx, ly, offset_x, offset_y, radius, occluders
                )
            else:
                self._draw_shadow_volumes_optimized(
                    light_surf, sr_key, lx, ly, offset_x, offset_y, radius, occluders
                )

        # Composite (clipped)
        self.lightmap.blit(light_surf, clip_rect, special_flags=pygame.BLEND_ADD)

        # Return surface before releasing to pool (for caching)
        result = light_surf

        # Release surface back to pool
        self.surface_pool.release(light_surf)

        return result

    def _draw_soft_shadows(
        self,
        light_surf: pygame.Surface,
        sr_key: int,
        lx: float,
        ly: float,
        offset_x: int,
        offset_y: int,
        radius: float,
        occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ],
    ) -> None:
        """
        Draws soft shadows efficiently using a downscale-upscale blur technique.

        Technique:
        1. Render hard shadows to a low-resolution surface (1/3 scale).
        2. Upscale the shadow mask back to full resolution using bilinear interpolation (smoothscale).
        3. Multiply the light surface by this blurred shadow mask.

        This aproximates a gaussian blur without the high cost of per-pixel convolution.
        """
        surf_size = sr_key * 2

        # Mild downscale (3x reduction = smooth blur without pixelation)
        downscale = 3
        low_res_size = max(8, surf_size // downscale)

        # Create low-res shadow mask (white = lit, black = shadow)
        shadow_mask = pygame.Surface((low_res_size, low_res_size))
        shadow_mask.fill((255, 255, 255))  # Start fully lit (white)

        # Transform params for low-res space
        low_res_scale = low_res_size / surf_size
        hx = low_res_size / 2.0
        hy = low_res_size / 2.0
        extrude_dist = radius * 2.0
        scale = self.scale * low_res_scale

        # Effective offset for low-res
        off_x_scaled = offset_x * low_res_scale
        off_y_scaled = offset_y * low_res_scale

        # Draw shadow quads to low-res surface (black = shadow)
        for _, vertices in occluders:
            n = len(vertices)
            if n < 2:
                continue
            for i in range(n):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % n]

                rel_x1 = p1[0] - lx
                rel_y1 = p1[1] - ly
                rel_x2 = p2[0] - lx
                rel_y2 = p2[1] - ly

                dist1_sq = rel_x1 * rel_x1 + rel_y1 * rel_y1
                dist2_sq = rel_x2 * rel_x2 + rel_y2 * rel_y2

                if dist1_sq < 0.000001:
                    dist1_sq = 0.000001
                if dist2_sq < 0.000001:
                    dist2_sq = 0.000001

                inv_dist1 = 1.0 / (dist1_sq**0.5)
                inv_dist2 = 1.0 / (dist2_sq**0.5)

                ex1_x = rel_x1 * inv_dist1 * extrude_dist
                ex1_y = rel_y1 * inv_dist1 * extrude_dist
                ex2_x = rel_x2 * inv_dist2 * extrude_dist
                ex2_y = rel_y2 * inv_dist2 * extrude_dist

                # Shadow bias: push shadow start points slightly away from occluder
                # This prevents shadow acne (self-shadowing artifacts)
                bias = 1.0  # pixels
                bias1_x = rel_x1 * inv_dist1 * bias
                bias1_y = rel_y1 * inv_dist1 * bias
                bias2_x = rel_x2 * inv_dist2 * bias
                bias2_y = rel_y2 * inv_dist2 * bias

                # Near points (with bias applied)
                q0_x = (p1[0] + bias1_x) * scale - off_x_scaled
                q0_y = (p1[1] + bias1_y) * scale - off_y_scaled
                q1_x = (p2[0] + bias2_x) * scale - off_x_scaled
                q1_y = (p2[1] + bias2_y) * scale - off_y_scaled
                # Far points (extruded)
                q2_x = (p2[0] + ex2_x) * scale - off_x_scaled
                q2_y = (p2[1] + ex2_y) * scale - off_y_scaled
                q3_x = (p1[0] + ex1_x) * scale - off_x_scaled
                q3_y = (p1[1] + ex1_y) * scale - off_y_scaled

                # Draw BLACK shadow (will become dark after blur)
                pygame.draw.polygon(
                    shadow_mask,
                    (0, 0, 0),
                    [(q0_x, q0_y), (q1_x, q1_y), (q2_x, q2_y), (q3_x, q3_y)],
                )

        # Single-pass blur via smoothscale
        blurred_mask = pygame.transform.smoothscale(shadow_mask, (surf_size, surf_size))

        # Apply shadow mask via multiplicative blend
        # White (255,255,255) * light = light (no shadow)
        # Black (0,0,0) * light = black (full shadow)
        # Gray values = partial shadow (soft edges)
        light_surf.blit(blurred_mask, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def _draw_shadow_volumes_optimized(
        self,
        light_surf: pygame.Surface,
        sr_key: int,
        lx: float,
        ly: float,
        offset_x: int,
        offset_y: int,
        radius: float,
        occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ],
    ) -> None:
        """
        Optimized shadow volume drawing with reduced Python overhead.
        Pre-computes common values and minimizes per-vertex calculations.
        """
        # No Need for hx/hy centering offset when drawing relative to clip origin
        extrude_dist = radius * 2.0
        scale = self.scale

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

                inv_dist1 = 1.0 / (dist1_sq**0.5)
                inv_dist2 = 1.0 / (dist2_sq**0.5)

                # Extrusion (Far points) - normalized direction * extrude distance
                ex1_x = rel_x1 * inv_dist1 * extrude_dist
                ex1_y = rel_y1 * inv_dist1 * extrude_dist
                ex2_x = rel_x2 * inv_dist2 * extrude_dist
                ex2_y = rel_y2 * inv_dist2 * extrude_dist

                # Construct Quad in world space, then transform to local
                # World quad: p1, p2, p2+extrusion, p1+extrusion
                # Transform: (world * scale - screen_pos) + half_size

                # Inline coordinate transform for speed
                # Inline coordinate transform for speed
                # ScreenPos = World * Scale
                # SurfacePos = ScreenPos - Offset
                q0_x = p1[0] * scale - offset_x
                q0_y = p1[1] * scale - offset_y
                q1_x = p2[0] * scale - offset_x
                q1_y = p2[1] * scale - offset_y
                q2_x = (p2[0] + ex2_x) * scale - offset_x
                q2_y = (p2[1] + ex2_y) * scale - offset_y
                q3_x = (p1[0] + ex1_x) * scale - offset_x
                q3_y = (p1[1] + ex1_y) * scale - offset_y

                # Draw opaque black to erase light
                pygame.draw.polygon(
                    light_surf,
                    (0, 0, 0, 255),
                    [(q0_x, q0_y), (q1_x, q1_y), (q2_x, q2_y), (q3_x, q3_y)],
                )

    def _draw_shadow_volumes_numpy(
        self,
        light_surf: pygame.Surface,
        sr_key: int,
        lx: float,
        ly: float,
        offset_x: int,
        offset_y: int,
        radius: float,
        occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ],
    ) -> None:
        """
        NumPy-accelerated shadow volume drawing.

        Uses vectorized operations to calculate all shadow quad vertices for an occluder in parallel.
        This provides a significant speedup over standard Python loops for geometry processing.
        """
        extrude_dist = radius * 2.0
        scale = self.scale

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
            # Calculate quad corners in local surface space
            # q0 = p1, q1 = p2, q2 = p2 + ex2, q3 = p1 + ex1
            # Transform: (world * scale - offset)
            q0 = (p1 * scale) - np.array([offset_x, offset_y])
            q1 = (p2 * scale) - np.array([offset_x, offset_y])
            q2 = ((p2 + ex2) * scale) - np.array([offset_x, offset_y])
            q3 = ((p1 + ex1) * scale) - np.array([offset_x, offset_y])

            # Draw each shadow quad
            for i in range(n):
                pygame.draw.polygon(
                    light_surf,
                    (0, 0, 0, 255),
                    [
                        (q0[i, 0], q0[i, 1]),
                        (q1[i, 0], q1[i, 1]),
                        (q2[i, 0], q2[i, 1]),
                        (q3[i, 0], q3[i, 1]),
                    ],
                )

    def _get_gradient_surface(
        self, radius: int, color: tuple[int, int, int], intensity: float
    ) -> pygame.Surface:
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

    def _generate_gradient_numpy(
        self, radius: int, color: tuple[int, int, int], intensity: float
    ) -> pygame.Surface:
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

    def _generate_gradient_pygame(
        self, radius: int, color: tuple[int, int, int], intensity: float
    ) -> pygame.Surface:
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
            alpha_val = int(base_alpha * (fn**2))

            # Draw ring with width 3 to cover gaps from larger step size
            pygame.draw.circle(surf, color + (alpha_val,), center, r, width=3)

        # Fill center
        pygame.draw.circle(surf, color + (base_alpha,), center, 3)

        return surf

    def _render_gradient_direct(
        self,
        target_surf: pygame.Surface,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[int, int, int],
        intensity: float,
    ) -> None:
        """
        Renders a gradient directly onto the target surface centered at (cx, cy).
        Used for large lights to avoid allocating huge cached textures.
        """
        if HAS_NUMPY:
            self._render_gradient_direct_numpy(
                target_surf, cx, cy, radius, color, intensity
            )
        else:
            self._render_gradient_direct_pygame(
                target_surf, cx, cy, radius, color, intensity
            )

    def _render_gradient_direct_numpy(
        self,
        target_surf: pygame.Surface,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[int, int, int],
        intensity: float,
    ) -> None:
        w, h = target_surf.get_size()
        sr = radius * self.scale

        # Coordinate grids
        x = np.arange(w, dtype=np.float32) - cx + 0.5
        y = np.arange(h, dtype=np.float32) - cy + 0.5
        xx, yy = np.meshgrid(x, y)

        # Dist
        dist = np.sqrt(xx * xx + yy * yy) / max(sr, 1.0)

        # Falloff
        falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2
        falloff = falloff * intensity

        # Colors
        r = (falloff * color[0]).astype(np.uint8)
        g = (falloff * color[1]).astype(np.uint8)
        b = (falloff * color[2]).astype(np.uint8)

        # Set pixels
        pixels = pygame.surfarray.pixels3d(target_surf)
        pixels[:, :, 0] = r.T
        pixels[:, :, 1] = g.T
        pixels[:, :, 2] = b.T
        del pixels

    def _render_gradient_direct_pygame(
        self,
        target_surf: pygame.Surface,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[int, int, int],
        intensity: float,
    ) -> None:
        """
        Fallback direct rendering using concentric circles.
        Since Pygame clips drawing, we can just draw huge circles.
        """
        sr = int(radius * self.scale)
        base_alpha = max(0, min(255, int(255 * intensity)))
        center = (int(cx), int(cy))

        # Coarse steps for performance
        steps = max(1, sr // 4)

        for i in range(steps):
            t = i / float(steps)
            r = int(sr * (1.0 - t))
            if r <= 0:
                continue

            fn = t
            alpha_val = int(base_alpha * (fn**2))

            # Draw circle (Pygame clips automatically)
            # Use width=5 to fill gaps
            pygame.draw.circle(target_surf, color + (alpha_val,), center, r, width=5)

        pygame.draw.circle(target_surf, color + (base_alpha,), center, 5)

    def get_surface(self) -> pygame.Surface:
        """
        Returns the final lightmap.
        Fast path: skip transform if scale is 1.0 (native resolution).
        """
        # Fast path - no scaling needed
        if self.scale == 1.0:
            return self.lightmap

        return pygame.transform.smoothscale(self.lightmap, self.native_size)

    def _query_grid(
        self, lx: float, ly: float, radius: float
    ) -> list[tuple[tuple[float, float, float, float], list[tuple[float, float]]]]:
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

                            if not (
                                oma_x < min_x
                                or omi_x > max_x
                                or oma_y < min_y
                                or omi_y > max_y
                            ):
                                candidates.append(occluder)
                                seen.add(occ_id)
        return candidates
