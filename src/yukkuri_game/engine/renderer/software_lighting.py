"""
Software Lighting Engine Module.
"""

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
    """

    def __init__(self, max_pool_size: int = 32) -> None:
        self._pool: dict[tuple[int, int], list[pygame.Surface]] = {}
        self._max_pool_size = max_pool_size

    def acquire(self, width: int, height: int) -> pygame.Surface:
        key = (width, height)
        if key in self._pool and self._pool[key]:
            surf = self._pool[key].pop()
            surf.fill((0, 0, 0, 0))
            return surf
        return pygame.Surface((width, height), pygame.SRCALPHA)

    def release(self, surf: pygame.Surface) -> None:
        key = surf.get_size()
        if key not in self._pool:
            self._pool[key] = []
        if len(self._pool[key]) < self._max_pool_size:
            self._pool[key].append(surf)


class SoftwareLightingEngine:
    """
    Optimized software lighting engine for Pygame.
    """

    def __init__(self, screen_size: tuple[int, int], scale: float = 1.0) -> None:
        self.scale = scale
        self.native_size = screen_size
        self.lightmap_size = (int(screen_size[0] * scale), int(screen_size[1] * scale))
        self.lightmap = pygame.Surface(self.lightmap_size)
        self.cell_size = 100
        self.grid: dict[
            tuple[int, int],
            list[tuple[tuple[float, float, float, float], list[tuple[float, float]]]],
        ] = {}
        self.occluders: list[
            tuple[tuple[float, float, float, float], list[tuple[float, float]]]
        ] = []
        self.light_texture_cache: dict[
            tuple[int, tuple[int, int, int], int], pygame.Surface
        ] = {}
        self.static_light_cache: dict[
            int, tuple[pygame.Surface, tuple[int, tuple[int, int, int], int, bool]]
        ] = {}
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
        self.lightmap.fill(ambient_color)
        self.occluders.clear()
        self.grid.clear()

    def add_occluder(
        self,
        aabb: tuple[float, float, float, float],
        vertices: list[tuple[float, float]],
    ) -> None:
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
        lx, ly = position
        sx = int(lx * self.scale)
        sy = int(ly * self.scale)
        sr = radius * self.scale
        if sr > 500:
            sr = round(sr / 50.0) * 50.0
        elif sr > 100:
            sr = round(sr / 10.0) * 10.0
        sr_key = int(max(1, sr))
        light_rect = pygame.Rect(sx - sr, sy - sr, sr * 2, sr * 2)
        screen_rect = self.lightmap.get_rect()
        clip_rect = light_rect.clip(screen_rect)
        if clip_rect.width <= 0 or clip_rect.height <= 0:
            return
        if static and entity_id >= 0:
            cache_key = (sr_key, color, int(intensity * 100), soft_shadows)
            if entity_id in self.static_light_cache:
                cached_surf, cached_key = self.static_light_cache[entity_id]
                if cached_key == cache_key:
                    dest_rect = cached_surf.get_rect(center=(sx, sy))
                    self.lightmap.blit(
                        cached_surf, dest_rect, special_flags=pygame.BLEND_ADD
                    )
                    return
        relevant_occluders = self._query_grid(lx, ly, radius)
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
        if static and entity_id >= 0 and light_surf is not None:
            cache_key = (sr_key, color, int(intensity * 100), soft_shadows)
            cached_copy = light_surf.copy()
            self.static_light_cache[entity_id] = (cached_copy, cache_key)
        if light_surf is not None:
            self.surface_pool.release(light_surf)

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
        surf_w, surf_h = clip_rect.size
        sx_center = lx * self.scale
        sy_center = ly * self.scale
        gx = clip_rect.x - (int(sx_center) - sr_key)
        gy = clip_rect.y - (int(sy_center) - sr_key)
        offset_x = clip_rect.x
        offset_y = clip_rect.y
        light_surf = self.surface_pool.acquire(surf_w, surf_h)
        if sr_key > 500:
            cx = (lx * self.scale) - clip_rect.x
            cy = (ly * self.scale) - clip_rect.y
            self._render_gradient_direct(light_surf, cx, cy, radius, color, intensity)
        else:
            grad_surf = self._get_gradient_surface(sr_key, color, intensity)
            sub_rect = pygame.Rect(gx, gy, surf_w, surf_h)
            light_surf.blit(grad_surf, (0, 0), area=sub_rect)
        if occluders:
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
        self.lightmap.blit(light_surf, clip_rect, special_flags=pygame.BLEND_ADD)
        return light_surf

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
        surf_size = sr_key * 2
        downscale = 3
        low_res_size = max(8, surf_size // downscale)
        shadow_mask = pygame.Surface((low_res_size, low_res_size))
        shadow_mask.fill((255, 255, 255))
        low_res_scale = low_res_size / surf_size
        extrude_dist = radius * 2.0
        scale = self.scale * low_res_scale
        off_x_scaled = offset_x * low_res_scale
        off_y_scaled = offset_y * low_res_scale
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
                if dist1_sq < 0.000001: dist1_sq = 0.000001
                if dist2_sq < 0.000001: dist2_sq = 0.000001
                inv_dist1 = 1.0 / (dist1_sq**0.5)
                inv_dist2 = 1.0 / (dist2_sq**0.5)
                ex1_x = rel_x1 * inv_dist1 * extrude_dist
                ex1_y = rel_y1 * inv_dist1 * extrude_dist
                ex2_x = rel_x2 * inv_dist2 * extrude_dist
                ex2_y = rel_y2 * inv_dist2 * extrude_dist
                bias = 1.0
                bias1_x = rel_x1 * inv_dist1 * bias
                bias1_y = rel_y1 * inv_dist1 * bias
                bias2_x = rel_x2 * inv_dist2 * bias
                bias2_y = rel_y2 * inv_dist2 * bias
                q0_x = (p1[0] + bias1_x) * scale - off_x_scaled
                q0_y = (p1[1] + bias1_y) * scale - off_y_scaled
                q1_x = (p2[0] + bias2_x) * scale - off_x_scaled
                q1_y = (p2[1] + bias2_y) * scale - off_y_scaled
                q2_x = (p2[0] + ex2_x) * scale - off_x_scaled
                q2_y = (p2[1] + ex2_y) * scale - off_y_scaled
                q3_x = (p1[0] + ex1_x) * scale - off_x_scaled
                q3_y = (p1[1] + ex1_y) * scale - off_y_scaled
                pygame.draw.polygon(
                    shadow_mask,
                    (0, 0, 0),
                    [(q0_x, q0_y), (q1_x, q1_y), (q2_x, q2_y), (q3_x, q3_y)],
                )
        blurred_mask = pygame.transform.smoothscale(shadow_mask, (surf_size, surf_size))
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
        extrude_dist = radius * 2.0
        scale = self.scale
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
                if dist1_sq < 0.000001: dist1_sq = 0.000001
                if dist2_sq < 0.000001: dist2_sq = 0.000001
                inv_dist1 = 1.0 / (dist1_sq**0.5)
                inv_dist2 = 1.0 / (dist2_sq**0.5)
                ex1_x = rel_x1 * inv_dist1 * extrude_dist
                ex1_y = rel_y1 * inv_dist1 * extrude_dist
                ex2_x = rel_x2 * inv_dist2 * extrude_dist
                ex2_y = rel_y2 * inv_dist2 * extrude_dist
                q0_x = p1[0] * scale - offset_x
                q0_y = p1[1] * scale - offset_y
                q1_x = p2[0] * scale - offset_x
                q1_y = p2[1] * scale - offset_y
                q2_x = (p2[0] + ex2_x) * scale - offset_x
                q2_y = (p2[1] + ex2_y) * scale - offset_y
                q3_x = (p1[0] + ex1_x) * scale - offset_x
                q3_y = (p1[1] + ex1_y) * scale - offset_y
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
        extrude_dist = radius * 2.0
        scale = self.scale
        for _, vertices in occluders:
            n = len(vertices)
            if n < 2:
                continue
            verts = np.array(vertices, dtype=np.float64)
            p1 = verts
            p2 = np.roll(verts, -1, axis=0)
            rel1 = p1 - np.array([lx, ly])
            rel2 = p2 - np.array([lx, ly])
            dist1_sq = np.sum(rel1 * rel1, axis=1)
            dist2_sq = np.sum(rel2 * rel2, axis=1)
            dist1_sq = np.maximum(dist1_sq, 0.000001)
            dist2_sq = np.maximum(dist2_sq, 0.000001)
            inv_dist1 = 1.0 / np.sqrt(dist1_sq)
            inv_dist2 = 1.0 / np.sqrt(dist2_sq)
            ex1 = rel1 * (inv_dist1 * extrude_dist)[:, np.newaxis]
            ex2 = rel2 * (inv_dist2 * extrude_dist)[:, np.newaxis]
            q0 = (p1 * scale) - np.array([offset_x, offset_y])
            q1 = (p2 * scale) - np.array([offset_x, offset_y])
            q2 = ((p2 + ex2) * scale) - np.array([offset_x, offset_y])
            q3 = ((p1 + ex1) * scale) - np.array([offset_x, offset_y])
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
        size = radius * 2
        if size < 1: size = 1
        x = np.arange(size, dtype=np.float32) - radius + 0.5
        y = np.arange(size, dtype=np.float32) - radius + 0.5
        xx, yy = np.meshgrid(x, y)
        dist = np.sqrt(xx * xx + yy * yy) / max(radius, 1)
        falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2
        falloff = falloff * intensity
        r = np.clip(falloff * color[0], 0, 255).astype(np.uint8)
        g = np.clip(falloff * color[1], 0, 255).astype(np.uint8)
        b = np.clip(falloff * color[2], 0, 255).astype(np.uint8)
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))
        pixels = pygame.surfarray.pixels3d(surf)
        pixels[:, :, 0] = r.T
        pixels[:, :, 1] = g.T
        pixels[:, :, 2] = b.T
        del pixels
        return surf

    def _generate_gradient_pygame(
        self, radius: int, color: tuple[int, int, int], intensity: float
    ) -> pygame.Surface:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = (radius, radius)
        base_alpha = max(0, min(255, int(255 * intensity)))
        steps = max(1, radius // 2)
        for i in range(steps):
            t = i / float(steps)
            r = int(radius * (1.0 - t))
            if r <= 0: continue
            fn = t
            alpha_val = int(base_alpha * (fn**2))
            pygame.draw.circle(surf, color + (alpha_val,), center, r, width=3)
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
        x = np.arange(w, dtype=np.float32) - cx + 0.5
        y = np.arange(h, dtype=np.float32) - cy + 0.5
        xx, yy = np.meshgrid(x, y)
        dist = np.sqrt(xx * xx + yy * yy) / max(sr, 1.0)
        falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2
        falloff = falloff * intensity
        r = np.clip(falloff * color[0], 0, 255).astype(np.uint8)
        g = np.clip(falloff * color[1], 0, 255).astype(np.uint8)
        b = np.clip(falloff * color[2], 0, 255).astype(np.uint8)
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
        sr = int(radius * self.scale)
        base_alpha = max(0, min(255, int(255 * intensity)))
        center = (int(cx), int(cy))
        steps = max(1, sr // 4)
        for i in range(steps):
            t = i / float(steps)
            r = int(sr * (1.0 - t))
            if r <= 0: continue
            fn = t
            alpha_val = min(255, int(255 * intensity * fn * fn))
            pygame.draw.circle(target_surf, color + (alpha_val,), center, r, width=5)
        pygame.draw.circle(target_surf, color + (base_alpha,), center, 5)

    def get_surface(self) -> pygame.Surface:
        if self.scale == 1.0:
            return self.lightmap
        return pygame.transform.smoothscale(self.lightmap, self.native_size)

    def _query_grid(
        self, lx: float, ly: float, radius: float
    ) -> list[tuple[tuple[float, float, float, float], list[tuple[float, float]]]]:
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
