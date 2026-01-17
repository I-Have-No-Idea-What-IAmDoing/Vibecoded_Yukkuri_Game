"""
Render System - Command-Based Rendering Pipeline.

Converts ECS state into render commands for the backend to execute.
Supports multiple backends (Pygame software, OpenGL hardware).

Pipeline Stages:
1. Camera update (interpolation, aspect correction)
2. Background grid (cached for performance)
3. Visible entity query (via SectorMap spatial partitioning)
4. Entity processing (sprites, shadows, lights, occluders)
5. Floating text overlay
6. Placement preview ghost sprite
7. Backend render execution

Layer System (z-ordering):
- LAYER_BACKGROUND (0): Grid, cached background
- LAYER_SHADOWS (1): Drop shadows under entities
- LAYER_ENTITIES (2): Sprites, sorted by Y position
- LAYER_EFFECTS (3): Lights, particles
- LAYER_UI (10): Floating text, selection UI

Optimizations:
- Background caching (invalidated on camera move)
- Scale quantization to reduce cache key permutations
- SectorMap culling for off-screen entities
- Surface caching for transformed sprites
"""

import pygame
import math
from typing import Any

from ...engine.ecs import System, World
from ...engine.resource_manager import ResourceManager
from ..camera import Camera
from ..components import (
    Transform,
    Sprite,
    VisualTransform,
    LightSource,
    Occluder,
    Selectable,
    FloatingText,
    PhysicsBody,
    FlickerStyle,
)
from ..yukkuri_components import Flight
from ..systems.sector_system import SectorMap
from ..services import TimeService
from ..surface_cache import SurfaceCache

from ..renderer.renderer import Renderer
from ..renderer.backend import RenderBackend
from ..renderer.pygame_backend import PygameBackend
from ..renderer.geometry_utils import GeometryUtils
from ..renderer.commands import (
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
)
from ..renderer.constants import RenderConstants

# ==================== LAYER CONSTANTS ====================
# Higher layers render on top. Entities sorted by Y within layer.
LAYER_BACKGROUND = 0  # Grid, terrain
LAYER_SHADOWS = 1  # Drop shadows (render before sprites)
LAYER_ENTITIES = 2  # Sprites, characters, items
LAYER_EFFECTS = 3  # Lights, particles, FX
LAYER_UI = 10  # Floating text, selection highlights


class RenderSystem(System):
    """
    Converts ECS world state into render commands.

    Uses a command pattern: entity state is converted to SpriteCommand,
    LightCommand, etc., then batch-processed by the backend for efficiency.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        world: World,
        lights_engine: Any = None,
        force_lighting: bool = False,
    ):
        self.screen = screen
        self.rm = world.services.get(ResourceManager)
        self.camera = world.services.get(Camera)
        self.surface_cache = SurfaceCache(self.rm)

        backend: RenderBackend
        # Select backend: OpenGLBackend if lights_engine is available, else PygameBackend.
        # TEMPORARY: Force PygameBackend as OpenGL backend is currently broken.
        if lights_engine is not None:
            # backend = OpenGLBackend(screen, lights_engine)
            # self.lights_enabled = True

            # Fallback to software renderer even if lights engine is provided
            backend = PygameBackend(screen)
            self.lights_enabled = True  # PygameBackend supports software lighting
        else:
            # PygameBackend now supports lighting natively via software
            backend = PygameBackend(screen)
            self.lights_enabled = True

        self.renderer = Renderer(backend)

        # Background Caching
        self._background_cache: pygame.Surface | None = None
        self._background_cache_valid: bool = False
        self._last_camera_state: tuple[int, int, float, int, int] | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Main render loop.
        """
        # Rename dt to alpha for clarity (it is interpolation alpha).
        alpha = dt
        sw, sh = self.screen.get_size()
        correction_x = 1.0
        correction_y = 1.0

        if self.lights_enabled:
            if hasattr(self.renderer.backend, "engine"):
                engine = getattr(self.renderer.backend, "engine", None)
                if engine and hasattr(engine, "_native_res"):
                    native_res: tuple[int, int] = getattr(engine, "_native_res")
                    nw, nh = native_res
                    current_w, current_h = self.screen.get_size()

                    if nw > 0 and nh > 0 and current_w > 0 and current_h > 0:
                        stretch_x = current_w / nw
                        stretch_y = current_h / nh
                        correction_x = (
                            stretch_y / stretch_x
                        )  # Pre-squash X for widescreen.

                    sw, sh = nw, nh

        self.camera.set_aspect_correction(correction_x, correction_y)
        self.camera.update_matrices(sw, sh, alpha)

        # 1. Clear & Draw Grid
        self.renderer.clear_screen((50, 50, 50))  # Dark background, but not pitch black

        # Manage Background Cache
        current_camera_state = (
            int(self.camera.camera_x),
            int(self.camera.camera_y),
            self.camera.zoom,
            sw,
            sh,
        )

        if current_camera_state != self._last_camera_state:
            self._background_cache_valid = False
            self._last_camera_state = current_camera_state

        # Skip grid when zoomed in past 5x (grid becomes sparse and less useful)
        if self.camera.zoom < 5.0:
            if not self._background_cache_valid or not self._background_cache:
                self._rebuild_background_cache(sw, sh)

            if self._background_cache and self._last_camera_state is not None:
                # Calculate sub-pixel offset for smooth scrolling.
                cached_cam_x, cached_cam_y, _, _, _ = self._last_camera_state

                diff_x = (cached_cam_x - self.camera.camera_x) * self.camera.zoom
                diff_y = (cached_cam_y - self.camera.camera_y) * self.camera.zoom

                final_x = (sw // 2) + diff_x
                final_y = (sh // 2) + diff_y

                self.renderer.submit(
                    SpriteCommand(
                        layer=LAYER_BACKGROUND,
                        z_index=-9999,  # Ensure it's behind everything
                        image=self._background_cache,
                        position=(final_x, final_y),
                        selected=False,
                        alpha=255,
                        cache_key=None,
                    )
                )

        # 2. Query Visible Entities
        visible_entities = self._get_visible_entities(world, sw, sh)

        # 3. Process Entities (skip static occluders as they are cached)
        for ent in visible_entities:
            self._process_entity(world, ent, alpha, sw, sh)

        # 4. Floating Text
        self._process_floating_text(world, sw, sh, alpha)

        # 5. Placement Preview (Submit before render)
        self._process_placement_preview(world, sw, sh)

        # 6. Render
        self.renderer.render()

    def _process_placement_preview(self, world: World, sw: int, sh: int) -> None:
        """
        Renders the placement preview (ghost sprite).

        Args:
            world (World): The ECS World.
            sw (int): Screen width.
            sh (int): Screen height.
        """
        # Lazy import to avoid circular dependency
        from ..services import InputService

        input_service = world.services.try_get(InputService)

        if not input_service or not input_service.is_placing:
            return

        image_name = input_service.place_image_name
        wx, wy = input_service.current_placement_pos

        sx, sy = self.camera.world_to_screen_fast(wx, wy)

        # Basic Fallback logic
        img = None
        if image_name:
            raw_surf = self.rm.load_image(image_name)
            if raw_surf:
                # Try to get correct width/height from item/yukkuri data
                place_type = input_service.place_type
                entity_type = input_service.place_entity_type

                sprite_width = 64  # Default
                sprite_height = 64

                if entity_type == "item" and place_type in self.rm.item_types:
                    item_data = self.rm.item_types[place_type]
                    sprite_width = getattr(item_data, "width", 32)
                    sprite_height = getattr(item_data, "height", 32)
                elif entity_type == "yukkuri" and place_type in self.rm.yukkuri_types:
                    yuk_data = self.rm.yukkuri_types[place_type]
                    sprite_width = getattr(yuk_data, "width", 64)
                    sprite_height = getattr(yuk_data, "height", 64)
                    # New Yukkuri start as babies - use shared constant
                    from ..yukkuri_constants import get_initial_scale

                    initial_scale = get_initial_scale()
                    sprite_width = int(sprite_width * initial_scale)
                    sprite_height = int(sprite_height * initial_scale)

                # Quantize scale to prevent cache thrashing.
                raw_scale = self.camera.zoom
                scale = round(raw_scale * 20.0) / 20.0

                final_w = int(sprite_width * scale)
                final_h = int(sprite_height * scale)

                if final_w > 0 and final_h > 0:
                    # Scale the entire loaded image to target size
                    img = pygame.transform.scale(raw_surf, (final_w, final_h))

        if not img:
            size = int(32 * self.camera.zoom)
            img = pygame.Surface((size, size), pygame.SRCALPHA)
            img.fill((0, 255, 0, 128))  # Fallback: semi-transparent green.

        if img:
            self.renderer.submit(
                SpriteCommand(
                    layer=LAYER_UI,
                    z_index=99999,
                    image=img,
                    position=(sx, sy),
                    selected=False,
                    alpha=128,  # Half transparent.
                    cache_key=None,
                )
            )

    def _get_visible_entities(self, world: World, sw: int, sh: int) -> list[int]:
        """Returns entities visible on screen using spatial partitioning."""
        sector_map = world.services.try_get(SectorMap)
        if sector_map:
            # Add buffer to catch entities at screen edges (large sprites may extend)
            buffer = 500.0

            # Convert screen corners to world coordinates
            start_x, start_y = self.camera.screen_to_world(0, 0, sw, sh)
            end_x, end_y = self.camera.screen_to_world(sw, sh, sw, sh)

            # Build query rectangle with buffer
            min_x = min(start_x, end_x) - buffer
            min_y = min(start_y, end_y) - buffer
            width = abs(end_x - start_x) + 2 * buffer
            height = abs(end_y - start_y) + 2 * buffer

            return sector_map.get_entities_in_rect(min_x, min_y, width, height)
        else:
            return [
                e for e, _ in world.get_components_tuple(Transform)
            ]  # Fallback: all entities.

    def _rebuild_background_cache(self, sw: int, sh: int) -> None:
        """
        Rebuilds the cached background surface (grid).
        """
        # Add margin for sub-pixel shift tolerance.
        margin = 32
        req_w, req_h = sw + margin * 2, sh + margin * 2

        if not self._background_cache or self._background_cache.get_size() != (
            req_w,
            req_h,
        ):
            self._background_cache = pygame.Surface((req_w, req_h), pygame.SRCALPHA)

        self._background_cache.fill((0, 0, 0, 0))

        # Draw grid at integer camera position for cache stability.
        cached_cam_x, cached_cam_y, cached_zoom, _, _ = self._last_camera_state  # type: ignore[misc]

        # Draw grid to cache surface.
        self._draw_grid(
            sw,
            sh,
            target_surface=self._background_cache,
            override_cam_pos=(cached_cam_x, cached_cam_y),
        )
        self._background_cache_valid = True

    def _draw_grid(
        self,
        sw: int,
        sh: int,
        target_surface: pygame.Surface | None = None,
        override_cam_pos: tuple[float, float] | None = None,
    ) -> None:
        grid_size = RenderConstants.GRID_SIZE
        color = RenderConstants.GRID_COLOR

        # Use override pos or current camera pos
        cam_x = override_cam_pos[0] if override_cam_pos else self.camera.camera_x
        cam_y = override_cam_pos[1] if override_cam_pos else self.camera.camera_y
        zoom = self.camera.zoom

        # Custom world_to_screen logic for this method to support override
        def world_to_screen(wx, wy):
            return ((wx - cam_x) * zoom + sw / 2, (wy - cam_y) * zoom + sh / 2)

        start_col, end_col, start_row, end_row = self._calculate_grid_bounds(
            sw, sh, grid_size, cam_x, cam_y
        )

        # Optimization: Batch line drawing if possible, or direct draw to surface
        if target_surface:
            # Draw directly to cache surface
            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = world_to_screen(x, 0)
                pygame.draw.line(target_surface, color, (sx, 0), (sx, sh))

            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = world_to_screen(0, y)
                pygame.draw.line(target_surface, color, (0, sy), (sw, sy))
        else:
            # Fallback to backend immediate draw (if cache is bypassed)
            # We still need to respect override_cam_pos if passed, but typically wouldn't be.
            # If backend.draw_line is used, it uses backend coords.
            # And we use self.camera.world_to_screen_fast usually.

            for col in range(start_col, end_col):
                x = col * grid_size
                # If override is provided, we must use custom transform
                if override_cam_pos:
                    sx, _ = world_to_screen(x, 0)
                else:
                    sx, _ = self.camera.world_to_screen_fast(x, 0)
                self.renderer.backend.draw_line((sx, 0), (sx, sh), color)

            for row in range(start_row, end_row):
                y = row * grid_size
                if override_cam_pos:
                    _, sy = world_to_screen(0, y)
                else:
                    _, sy = self.camera.world_to_screen_fast(0, y)
                self.renderer.backend.draw_line((0, sy), (sw, sy), color)

    def _calculate_grid_bounds(
        self,
        screen_w: int,
        screen_h: int,
        grid_size: int,
        cam_x: float | None = None,
        cam_y: float | None = None,
    ) -> tuple[int, int, int, int]:
        if cam_x is not None and cam_y is not None:
            # Custom calculation based on override pos
            # screen_to_world inverse:
            # wx = (sx - half_w) / zoom + cam_x
            half_w = screen_w / 2
            half_h = screen_h / 2
            zoom = self.camera.zoom

            start_x = (0 - half_w) / zoom + cam_x
            start_y = (0 - half_h) / zoom + cam_y
            end_x = (screen_w - half_w) / zoom + cam_x
            end_y = (screen_h - half_h) / zoom + cam_y
        else:
            start_x, start_y = self.camera.screen_to_world(0, 0, screen_w, screen_h)
            end_x, end_y = self.camera.screen_to_world(
                screen_w, screen_h, screen_w, screen_h
            )

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1
        return start_col, end_col, start_row, end_row

    def _process_entity(
        self, world: World, ent: int, alpha: float, sw: int, sh: int
    ) -> None:
        """Processes a single entity's visual components into render commands."""
        transform = world.try_get_component(ent, Transform)
        if not transform:
            return

        # Interpolate position for smooth rendering.
        ix = transform.x
        iy = transform.y
        if transform.prev_x is not None and transform.prev_y is not None:
            ix = transform.prev_x + (transform.x - transform.prev_x) * alpha
            iy = transform.prev_y + (transform.y - transform.prev_y) * alpha

        screen_pos = self.camera.world_to_screen_fast(ix, iy)

        # 1. Sprite & Shadow
        sprite = world.try_get_component(ent, Sprite)
        visual = world.try_get_component(ent, VisualTransform)

        if sprite and visual:
            # Quantize scale (0.05 increments) to prevent cache thrashing.
            raw_scale = transform.scale * self.camera.zoom
            scale = round(raw_scale * 20.0) / 20.0

            shadow_x, shadow_y = self.camera.world_to_screen_fast(
                ix + visual.shadow_position.x,
                iy + visual.shadow_position.y + feet_offset_y,
            )

            shadow_radius_x = sprite.width * scale * RenderConstants.SHADOW_SCALE_X
            shadow_radius_y = shadow_radius_x * RenderConstants.SHADOW_SCALE_Y

            # Flight-aware shadow scaling
            flight = world.try_get_component(ent, Flight)
            shadow_alpha = 100
            if flight and flight.max_altitude > 0:
                height_factor = min(
                    1.0, max(0.0, flight.altitude / flight.max_altitude)
                )
                # Scale: 100% -> 60% size as altitude increases
                shadow_radius_x *= 1.0 - 0.4 * height_factor
                shadow_radius_y *= 1.0 - 0.4 * height_factor
                # Alpha: 100 -> ~60 as altitude increases
                shadow_alpha = int(100 * (1.0 - 0.4 * height_factor))

            if shadow_radius_x > 0 and visual.has_drop_shadow:
                self.renderer.submit(
                    ShadowCommand(
                        layer=LAYER_SHADOWS,
                        z_index=iy,  # Shadow sorts with entity
                        position=(shadow_x, shadow_y),
                        radius=(shadow_radius_x, shadow_radius_y),
                        color=(0, 0, 0, shadow_alpha),
                    )
                )

            # Sprite
            # Get cached surface
            img = self.surface_cache.get_surface(
                sprite.image_name,
                sprite.current_frame,
                sprite.frame_count,
                sprite.width,
                sprite.height,
                scale,
                transform.rotation,
                sprite.flip_x,
                sprite.flip_y,
            )

            if img:
                selectable = world.try_get_component(ent, Selectable)
                is_selected = selectable.selected if selectable else False

                # Apply vertical offset (including flight altitude)
                flight_offset = 0.0
                if flight:
                    flight_offset = flight.altitude
                sprite_sy = screen_pos[1] - (
                    (visual.vertical_offset + flight_offset) * self.camera.zoom
                )

                cache_key = (
                    sprite.image_name,
                    sprite.current_frame,
                    round(scale, 3),
                    round(transform.rotation, 1),
                    sprite.flip_x,
                    sprite.flip_y,
                )  # Texture cache key for backend.

                self.renderer.submit(
                    SpriteCommand(
                        layer=LAYER_ENTITIES,
                        z_index=iy,
                        image=img,
                        position=(screen_pos[0], sprite_sy),
                        selected=is_selected,
                        alpha=sprite.alpha,
                        cache_key=cache_key,
                    )
                )

        # 2. Light
        if self.lights_enabled:
            light = world.try_get_component(ent, LightSource)
            if light:
                radius = light.radius * self.camera.zoom

                # Flicker Logic
                intensity = light.intensity
                if light.flicker_style != FlickerStyle.NONE:
                    time_service = world.services.try_get(TimeService)
                    time_elapsed = time_service.time_elapsed if time_service else 0.0

                    if light.flicker_style == FlickerStyle.FIRE:
                        noise = (
                            math.sin(time_elapsed * 10.0 + ent) * 0.1
                            + math.sin(time_elapsed * 23.0 + ent * 2) * 0.05
                            + math.sin(time_elapsed * 47.0 + ent * 0.5) * 0.02
                        )
                        intensity = light.intensity * (1.0 + noise)
                    elif light.flicker_style == FlickerStyle.PULSE:
                        intensity = light.intensity * (
                            0.8 + 0.2 * math.sin(time_elapsed * math.pi)
                        )

                # Ensure color is RGBA
                color = light.color
                if len(color) == 3:
                    color = (color[0], color[1], color[2], 255)

                self.renderer.submit(
                    LightCommand(
                        layer=LAYER_EFFECTS,  # Lights are handled specially by backend
                        z_index=iy,
                        entity_id=ent,
                        position=screen_pos,
                        radius=radius,
                        color=color,
                        intensity=intensity,
                        flicker_style=light.flicker_style,
                        soft_shadows=light.soft_shadows,
                        static=light.static,
                    )
                )

            occluder = world.try_get_component(ent, Occluder)
            if occluder:
                # Skip self-shadowing: don't render occluder if entity has active light.
                if light and light.intensity > 0:
                    pass
                else:
                    self._process_occluder(world, ent, transform, occluder, ix, iy)

    def _process_occluder(
        self,
        world: World,
        ent: int,
        transform: Transform,
        occluder: Occluder,
        ix: float,
        iy: float,
    ) -> None:
        sprite = world.try_get_component(ent, Sprite)
        body = world.try_get_component(ent, PhysicsBody)

        # Pass interpolated positions (ix, iy) to GeometryUtils
        world_verts = GeometryUtils.get_occluder_vertices(
            ent,
            transform,
            occluder,
            sprite,
            body,
            override_x=ix,
            override_y=iy,
        )

        if len(world_verts) < 3:
            return

        screen_verts = []
        for wx, wy in world_verts:
            sx, sy = self.camera.world_to_screen_fast(wx, wy)
            screen_verts.append((sx, sy))

        self.renderer.submit(
            OccluderCommand(
                layer=LAYER_BACKGROUND,
                z_index=0,
                entity_id=ent,
                vertices=screen_verts,
                static=occluder.static,
            )
        )

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        self.renderer.set_ambient_light(color)

    def _process_floating_text(
        self, world: World, sw: int, sh: int, alpha: float
    ) -> None:
        for ent, (transform, text) in world.get_components_tuple(
            Transform, FloatingText
        ):
            sx, sy = self.camera.world_to_screen_fast(transform.x, transform.y)

            if 0 <= sx <= sw and 0 <= sy <= sh:  # Cull offscreen.
                alpha_val = 255
                if text.max_lifetime > 0:
                    alpha_val = int(255 * (text.lifetime / text.max_lifetime))

                self.renderer.submit(
                    TextCommand(
                        layer=LAYER_UI,
                        z_index=transform.y + 1000,  # On top
                        text=text.text,
                        position=(sx, sy),
                        size=text.size,
                        color=text.color,
                        alpha=alpha_val,
                    )
                )
