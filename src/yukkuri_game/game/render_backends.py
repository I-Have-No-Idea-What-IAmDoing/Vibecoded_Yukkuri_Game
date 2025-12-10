import pygame
import pygame_light2d as pl2d
import math
from typing import Tuple, List, Optional, Callable, Dict
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass

from .camera import Camera
from .surface_cache import SurfaceCache
from .components import Transform, Sprite, VisualTransform, FloatingText, LightSource, Occluder, PhysicsBody

# Constants
class RenderConstants:
    GRID_SIZE: int = 100
    GRID_COLOR: Tuple[int, int, int] = (50, 50, 50)
    GRID_COLOR_FLOAT: Tuple[float, float, float, float] = (50/255, 50/255, 50/255, 1.0)
    SHADOW_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 100)
    SELECTION_COLOR: Tuple[int, int, int] = (255, 255, 0)
    SELECTION_COLOR_FLOAT: Tuple[float, float, float, float] = (1.0, 1.0, 0.0, 1.0)
    SELECTION_WIDTH: int = 2
    SHADOW_SCALE_X: float = 0.4
    SHADOW_SCALE_Y: float = 0.5
    CIRCLE_OCCLUDER_SEGMENTS: int = 12


@dataclass
class EntityRenderState:
    """Holds calculated render state for an entity."""
    screen_x: int
    screen_y: int
    scale: float
    rect: pygame.Rect
    is_visible: bool
    shadow_props: Optional[Tuple[int, int, int, int]]  # radius_x, radius_y, x, y


class RenderBackend(ABC):
    """
    Abstract base class for rendering backends.

    Provides common functionality for coordinate transformation,
    caching, and helper methods.
    """

    def __init__(self) -> None:
        self.font_cache: Dict[int, pygame.font.Font] = {}

    def _get_font(self, size: int) -> pygame.font.Font:
        """Retrieves a cached font object."""
        if size not in self.font_cache:
            self.font_cache[size] = pygame.font.SysFont(None, size)
        return self.font_cache[size]

    def _get_interpolated_position(self, transform: Transform, alpha: float) -> Tuple[float, float]:
        """Calculates the interpolated world position."""
        curr_x = transform.x
        curr_y = transform.y
        # Transform's __post_init__ guarantees prev_x/y are set
        prev_x = transform.prev_x
        prev_y = transform.prev_y

        interp_x = prev_x + (curr_x - prev_x) * alpha
        interp_y = prev_y + (curr_y - prev_y) * alpha
        return interp_x, interp_y

    def _calculate_grid_bounds(self, camera: Camera, screen_w: int, screen_h: int) -> Tuple[int, int, int, int]:
        """Calculates the grid column and row ranges visible on screen."""
        start_x, start_y = camera.screen_to_world(0, 0, screen_w, screen_h)
        end_x, end_y = camera.screen_to_world(screen_w, screen_h, screen_w, screen_h)

        start_col = int(start_x // RenderConstants.GRID_SIZE)
        end_col = int(end_x // RenderConstants.GRID_SIZE) + 1
        start_row = int(start_y // RenderConstants.GRID_SIZE)
        end_row = int(end_y // RenderConstants.GRID_SIZE) + 1

        return start_col, end_col, start_row, end_row

    def _create_shadow_surface_factory(self, radius_x: int, radius_y: int) -> Callable[[], pygame.Surface]:
        """Returns a factory function for creating a shadow surface."""
        def factory() -> pygame.Surface:
            surface = pygame.Surface((radius_x * 2, radius_y * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(surface, RenderConstants.SHADOW_COLOR, surface.get_rect())
            return surface
        return factory

    def _calculate_shadow_properties(
        self,
        camera: Camera,
        sprite: Sprite,
        visual_transform: VisualTransform,
        scale: float,
        sw: int,
        sh: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculates the shadow radius and screen position.
        Returns None if shadow shouldn't be drawn.
        Returns: (radius_x, radius_y, screen_x, screen_y)
        """
        shadow_radius_x = int(sprite.width * scale * RenderConstants.SHADOW_SCALE_X)
        shadow_radius_y = int(shadow_radius_x * RenderConstants.SHADOW_SCALE_Y)

        if shadow_radius_x <= 0 or shadow_radius_y <= 0:
            return None

        shadow_x, shadow_y = camera.world_to_screen(
            visual_transform.shadow_position.x,
            visual_transform.shadow_position.y,
            sw,
            sh,
        )
        return shadow_radius_x, shadow_radius_y, int(shadow_x), int(shadow_y)

    def _prepare_entity_state(
        self,
        camera: Camera,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        alpha: float,
        width: int,
        height: int,
        screen_rect: pygame.Rect,
        scale: float
    ) -> EntityRenderState:
        """
        Calculates common entity render properties.
        """
        interp_x, interp_y = self._get_interpolated_position(transform, alpha)
        sw, sh = screen_rect.width, screen_rect.height

        base_screen_x, base_screen_y = camera.world_to_screen(
            interp_x, interp_y, sw, sh
        )
        screen_y = base_screen_y - (visual_transform.vertical_offset * camera.zoom)
        screen_x = base_screen_x

        rect = pygame.Rect(0, 0, width, height)
        rect.center = (int(screen_x), int(screen_y))

        is_visible = rect.colliderect(screen_rect)

        shadow_props = None
        if is_visible:
             shadow_props = self._calculate_shadow_properties(camera, sprite, visual_transform, scale, sw, sh)

        return EntityRenderState(
            screen_x=int(screen_x),
            screen_y=int(screen_y),
            scale=scale,
            rect=rect,
            is_visible=is_visible,
            shadow_props=shadow_props
        )

    @abstractmethod
    def clear(self) -> None:
        """Clears the screen or prepares for a new frame."""
        pass

    @abstractmethod
    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int) -> None:
        """Draws the world grid."""
        pass

    @abstractmethod
    def draw_entity(
        self,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ) -> None:
        """Draws a single entity (shadow + sprite + selection)."""
        pass

    @abstractmethod
    def draw_floating_text(
        self,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ) -> None:
        """Draws floating text."""
        pass


class PygameRenderBackend(RenderBackend):
    """
    Standard Pygame rendering backend.
    """
    def __init__(self, screen: pygame.Surface) -> None:
        super().__init__()
        self.screen = screen
        self.shadow_cache: Dict[Tuple[int, int], pygame.Surface] = {}

    def clear(self) -> None:
        # In standard pygame, we usually fill screen, but WorldRenderer might handle background.
        pass

    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int) -> None:
        start_col, end_col, start_row, end_row = self._calculate_grid_bounds(camera, screen_w, screen_h)

        for col in range(start_col, end_col):
            x = col * RenderConstants.GRID_SIZE
            sx, _ = camera.world_to_screen(x, 0, screen_w, screen_h)
            pygame.draw.line(self.screen, RenderConstants.GRID_COLOR, (int(sx), 0), (int(sx), screen_h))

        for row in range(start_row, end_row):
            y = row * RenderConstants.GRID_SIZE
            _, sy = camera.world_to_screen(0, y, screen_w, screen_h)
            pygame.draw.line(self.screen, RenderConstants.GRID_COLOR, (0, int(sy)), (screen_w, int(sy)))

    def _get_shadow_surface(self, radius_x: int, radius_y: int) -> pygame.Surface:
        key = (radius_x, radius_y)
        if key not in self.shadow_cache:
            self.shadow_cache[key] = self._create_shadow_surface_factory(radius_x, radius_y)()
        return self.shadow_cache[key]

    def draw_entity(
        self,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ) -> None:
        # We need the surface first to know the size for visibility check
        # But calculating the surface might be expensive if not cached?
        # SurfaceCache should be fast.

        # Calculate scale first
        scale = transform.scale * camera.zoom

        scaled_img = surface_cache.get_surface(
            sprite.image_name,
            sprite.current_frame,
            sprite.frame_count,
            sprite.width,
            sprite.height,
            scale,
            transform.rotation,
            sprite.flip_x,
            sprite.flip_y
        )

        if not scaled_img:
            return

        state = self._prepare_entity_state(
            camera,
            transform,
            sprite,
            visual_transform,
            alpha,
            scaled_img.get_width(),
            scaled_img.get_height(),
            self.screen.get_rect(),
            scale
        )

        if state.is_visible:
            # Draw Shadow
            if state.shadow_props:
                radius_x, radius_y, sx, sy = state.shadow_props
                shadow_surf = self._get_shadow_surface(radius_x, radius_y)
                self.screen.blit(shadow_surf, (sx - radius_x, sy - radius_y))

            # Draw Sprite
            # Correct the rect center as _prepare_entity_state sets it based on dimensions
            # which matches scaled_img size.
            self.screen.blit(scaled_img, state.rect)

            # Draw Selection
            if is_selected:
                pygame.draw.rect(
                    self.screen,
                    RenderConstants.SELECTION_COLOR,
                    state.rect,
                    RenderConstants.SELECTION_WIDTH
                )

    def draw_floating_text(
        self,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ) -> None:
        font = self._get_font(text_comp.size)
        text_surface = font.render(text_comp.text, True, text_comp.color)

        if text_comp.max_lifetime > 0:
            alpha_val = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
            alpha_val = max(0, min(255, alpha_val))
            text_surface.set_alpha(alpha_val)

        screen_x, screen_y = camera.world_to_screen(
            transform.x, transform.y, screen_w, screen_h
        )
        rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))
        self.screen.blit(text_surface, rect)


class Light2DRenderBackend(RenderBackend):
    """
    Pygame Light2D rendering backend.
    """

    def __init__(
        self,
        lights_engine: pl2d.LightingEngine,
        screen: pygame.Surface,
        texture_cache_max_size: int = 500,
    ) -> None:
        super().__init__()
        self.lights_engine = lights_engine
        self.screen = screen
        self.texture_cache: OrderedDict[tuple, "pl2d.Texture"] = OrderedDict()
        self.texture_cache_max_size = texture_cache_max_size

        # Persistent Light/Hull management
        # Map entity_id -> pl2d.PointLight / pl2d.Hull
        self.active_lights: Dict[int, pl2d.PointLight] = {}
        self.active_hulls: Dict[int, pl2d.Hull] = {}

        # Track transform state to avoid unnecessary Hull rebuilds
        # Map entity_id -> (x, y, rotation, scale, sprite_width, sprite_height)
        self.hull_transform_state: Dict[int, Tuple[float, float, float, float, int, int]] = {}

        # Track camera state for global invalidation
        self._last_camera_state: Optional[Tuple[float, float, float]] = None

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        """Sets the ambient light color."""
        self.lights_engine.set_ambient(color)

    def update_lights(self, lights_data: List[Tuple[int, Transform, LightSource]], camera: Camera) -> None:
        """
        Syncs ECS LightSource components with the engine.
        Args:
            lights_data: List of (entity_id, Transform, LightSource)
            camera: The camera for visibility check.
        """
        # Track which entities are processed this frame to identify removals
        processed_ids = set()
        screen_w, screen_h = self.screen.get_size()
        screen_rect = pygame.Rect(0, 0, screen_w, screen_h)
        # Inflate screen rect for culling tolerance
        cull_rect = screen_rect.inflate(200, 200)

        for ent_id, transform, light_comp in lights_data:
            # 1. Culling Check
            # We transform world pos to screen pos to check against screen rect
            # Note: Light engine works in screen coordinates (native res).
            # If native res != screen res, we might need conversion, but usually they match or scale.
            # Assuming camera.world_to_screen gives coordinates relevant to the light engine's view.

            # Simple world-space culling might be easier if we know camera bounds in world space
            # But let's stick to screen space projection for now
            screen_x, screen_y = camera.world_to_screen(transform.x, transform.y, screen_w, screen_h)

            # Use radius to expand check
            light_rect = pygame.Rect(0, 0, 0, 0)
            # Center the rect
            light_radius_screen = light_comp.radius * camera.zoom
            light_rect.width = light_radius_screen * 2
            light_rect.height = light_radius_screen * 2
            light_rect.center = (screen_x, screen_y)

            if not cull_rect.colliderect(light_rect):
                # Light is off-screen. If it was active, remove it.
                if ent_id in self.active_lights:
                    self.lights_engine.lights.remove(self.active_lights[ent_id])
                    del self.active_lights[ent_id]
                continue

            processed_ids.add(ent_id)

            # 2. Update or Create Light
            if ent_id not in self.active_lights:
                # Create new light
                pl_light = pl2d.PointLight(
                    position=(screen_x, screen_y),
                    power=light_comp.intensity,
                    radius=light_radius_screen
                )
                pl_light.set_color(*light_comp.color)
                self.lights_engine.lights.append(pl_light)
                self.active_lights[ent_id] = pl_light
            else:
                # Update existing light
                pl_light = self.active_lights[ent_id]
                pl_light.position = (screen_x, screen_y)
                pl_light.power = light_comp.intensity
                pl_light.radius = light_radius_screen
                pl_light.set_color(*light_comp.color)

        # 3. Cleanup Stale Lights
        stale_ids = self.active_lights.keys() - processed_ids
        if stale_ids:
            stale_lights_set = {self.active_lights[eid] for eid in stale_ids}
            self.lights_engine.lights[:] = [
                light for light in self.lights_engine.lights if light not in stale_lights_set
            ]
            for eid in stale_ids:
                del self.active_lights[eid]

    def update_occluders(
        self,
        occluders_data: List[Tuple[int, Transform, Occluder, Optional[Sprite], Optional[PhysicsBody]]],
        camera: Camera
    ) -> None:
        """
        Syncs ECS Occluder components with the engine.
        Args:
            occluders_data: List of (entity_id, Transform, Occluder, Sprite?, PhysicsBody?)
            camera: The camera.
        """
        processed_ids = set()
        screen_w, screen_h = self.screen.get_size()
        screen_rect = pygame.Rect(0, 0, screen_w, screen_h)
        cull_rect = screen_rect.inflate(100, 100)

        # Invalidate cache if camera changed
        current_camera_state = (camera.camera_x, camera.camera_y, camera.zoom)
        if self._last_camera_state != current_camera_state:
            # Camera moved: Screen coordinates for all static objects are invalid.
            # We must force a rebuild of all hulls.
            # However, removing/re-adding Hulls is expensive if list is large.
            # Ideally we'd modify vertices in place, but pygame_light2d Hull vertices might be read-only or cached internally by it.
            # Safe bet: Clear our transform state cache to force rebuild.
            self.hull_transform_state.clear()
            self._last_camera_state = current_camera_state

        for ent_id, transform, occluder, sprite, body in occluders_data:

            # Optimization: Check if state changed
            # Key state vars: x, y, rot, scale. Sprite dims if sprite fallback.
            sprite_w = sprite.width if sprite else 0
            sprite_h = sprite.height if sprite else 0

            current_state = (transform.x, transform.y, transform.rotation, transform.scale, sprite_w, sprite_h)

            # If we have an active hull and state matches, skip calculation
            if ent_id in self.active_hulls and ent_id in self.hull_transform_state:
                if self.hull_transform_state[ent_id] == current_state:
                    processed_ids.add(ent_id)
                    continue

            # 1. Determine Vertices
            # We need world space vertices first, then convert to screen space

            world_vertices = []

            if occluder.polygon:
                # Use custom polygon relative to transform
                # Rotate and translate
                rad = math.radians(transform.rotation)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                for vx, vy in occluder.polygon:
                    # Apply rotation
                    rx = vx * cos_a - vy * sin_a
                    ry = vx * sin_a + vy * cos_a
                    # Apply scale (assume uniform for now or x scale)
                    rx *= transform.scale
                    ry *= transform.scale

                    world_vertices.append((transform.x + rx, transform.y + ry))
            elif body:
                 # Use physics shape if available (best for walls)
                 if hasattr(body.shape, 'get_vertices'):
                     # Poly
                     for v in body.shape.get_vertices():
                         wv = body.body.local_to_world(v)
                         world_vertices.append((wv.x, wv.y))
                 elif isinstance(body.shape, pymunk.Segment):
                     # Line segment wall
                     v1 = body.body.local_to_world(body.shape.a)
                     v2 = body.body.local_to_world(body.shape.b)

                     # Extrude segment into a thin quad (e.g. 4px thick)
                     # Vector direction
                     dx = v2.x - v1.x
                     dy = v2.y - v1.y
                     length = (dx*dx + dy*dy)**0.5
                     if length > 0.001:
                         nx = -dy / length
                         ny = dx / length
                         thickness = 2.0 # Half thickness

                         world_vertices.append((v1.x + nx * thickness, v1.y + ny * thickness))
                         world_vertices.append((v2.x + nx * thickness, v2.y + ny * thickness))
                         world_vertices.append((v2.x - nx * thickness, v2.y - ny * thickness))
                         world_vertices.append((v1.x - nx * thickness, v1.y - ny * thickness))
                     else:
                         # Degenerate segment
                         world_vertices.append((v1.x, v1.y))
                         world_vertices.append((v2.x, v2.y))

                 elif isinstance(body.shape, pymunk.Circle):
                     # Approximate circle with a polygon
                     num_segments = RenderConstants.CIRCLE_OCCLUDER_SEGMENTS
                     radius = body.shape.radius
                     for i in range(num_segments):
                         angle = 2 * math.pi * i / num_segments
                         # Get local coordinates relative to body center
                         vx = radius * math.cos(angle)
                         vy = radius * math.sin(angle)
                         # Convert to world coordinates
                         # Note: pymunk.Body.local_to_world expects a Vec2d or tuple
                         wv = body.body.local_to_world((vx, vy))
                         world_vertices.append((wv.x, wv.y))
            elif sprite:
                # Fallback to sprite rect (box)
                w = sprite.width * transform.scale
                h = sprite.height * transform.scale
                # Corners relative to center
                corners = [
                    (-w/2, -h/2),
                    (w/2, -h/2),
                    (w/2, h/2),
                    (-w/2, h/2)
                ]
                # Rotate
                rad = math.radians(transform.rotation)
                cos_a = math.cos(rad)
                sin_a = math.sin(rad)

                for vx, vy in corners:
                    rx = vx * cos_a - vy * sin_a
                    ry = vx * sin_a + vy * cos_a
                    world_vertices.append((transform.x + rx, transform.y + ry))

            # Hull requires at least 3 vertices
            if len(world_vertices) < 3:
                continue

            # 2. Culling
            # Check if any vertex is within cull_rect (projected)
            # Or bounding box of vertices
            min_x = min(v[0] for v in world_vertices)
            max_x = max(v[0] for v in world_vertices)
            min_y = min(v[1] for v in world_vertices)
            max_y = max(v[1] for v in world_vertices)

            # Project bounds to screen
            screen_min_x, screen_min_y = camera.world_to_screen(min_x, min_y, screen_w, screen_h)
            screen_max_x, screen_max_y = camera.world_to_screen(max_x, max_y, screen_w, screen_h)

            # Simple rect check (doesn't account for rotation perfectly but good enough for culling)
            # Actually world_to_screen flips Y, so min_y world might be max_y screen depending on axis
            # Let's just project all vertices
            screen_vertices = []
            for wx, wy in world_vertices:
                sx, sy = camera.world_to_screen(wx, wy, screen_w, screen_h)
                screen_vertices.append((sx, sy))

            xs = [v[0] for v in screen_vertices]
            ys = [v[1] for v in screen_vertices]
            obj_rect = pygame.Rect(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))

            if not cull_rect.colliderect(obj_rect):
                if ent_id in self.active_hulls:
                    self.lights_engine.hulls.remove(self.active_hulls[ent_id])
                    del self.active_hulls[ent_id]
                continue

            processed_ids.add(ent_id)

            # 3. Update/Create Hull
            # pygame_light2d Hull vertices are immutable?
            # Looking at source/docs: Hull(vertices, ...).
            # Changing vertices after init might not be supported or requires property set.
            # If not supported, we must recreate.
            # Assuming we need to recreate if geometry changes (moving objects).
            # For static objects (Walls), optimization would be to check if transform changed.
            # For now, let's just recreate if needed or update if possible.

            # Checking `help(Hull)` provided earlier: no explicit set_vertices.
            # It just has __init__.
            # So we likely need to recreate the Hull object if it moves.
            # Optimally we only do this if it moved.

            # Let's assume we replace it every frame for now, or check for equality?
            # Recreating Hulls every frame is expensive.
            # But `lights_engine.hulls` is a list.

            # Optimization: Only update if position changed?
            # But we don't track prev pos here easily without checking Transform.
            # Transform has prev_x, prev_y.

            # We delay modifying the engine's hull list until the end
            hull = pl2d.Hull(screen_vertices)
            self.active_hulls[ent_id] = hull
            self.hull_transform_state[ent_id] = current_state

        # Cleanup
        stale_ids = self.active_hulls.keys() - processed_ids
        if stale_ids:
            for eid in stale_ids:
                del self.active_hulls[eid]
                if eid in self.hull_transform_state:
                    del self.hull_transform_state[eid]

        # Rebuild the engine's hull list from active hulls
        # This avoids O(N) removals inside the loop
        self.lights_engine.hulls[:] = list(self.active_hulls.values())

    def clear(self) -> None:
        pass

    def _get_cached_texture(
        self,
        key: tuple,
        surface_generator: Callable[[], Optional[pygame.Surface]]
    ) -> Optional["pl2d.Texture"]:
        if key in self.texture_cache:
            self.texture_cache.move_to_end(key)
            return self.texture_cache[key]

        surface = surface_generator()
        if surface is None:
            return None

        tex = self.lights_engine.surface_to_texture(surface)
        self.texture_cache[key] = tex

        if len(self.texture_cache) > self.texture_cache_max_size:
            _, old_tex = self.texture_cache.popitem(last=False)
            old_tex.release()

        return tex

    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int) -> None:
        start_col, end_col, start_row, end_row = self._calculate_grid_bounds(camera, screen_w, screen_h)

        bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)
        vertices = []

        for col in range(start_col, end_col):
            x = col * RenderConstants.GRID_SIZE
            sx, _ = camera.world_to_screen(x, 0, screen_w, screen_h)
            vertices.extend([(sx, 0), (sx, screen_h)])

        for row in range(start_row, end_row):
            y = row * RenderConstants.GRID_SIZE
            _, sy = camera.world_to_screen(0, y, screen_w, screen_h)
            vertices.extend([(0, sy), (screen_w, sy)])

        if vertices:
            self.lights_engine.graphics.render_lines(
                bg_layer,
                RenderConstants.GRID_COLOR_FLOAT,
                vertices,
                antialias=False
            )

    def draw_entity(
        self,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ) -> None:
        # For Light2D, we need the texture.
        # We also need dimensions for culling, but texture gives us dimensions.

        interp_x, interp_y = self._get_interpolated_position(transform, alpha)
        scale = transform.scale * camera.zoom

        # Texture Key
        sprite_key = (
            sprite.image_name,
            sprite.current_frame,
            round(scale, 3),
            round(transform.rotation, 1),
            sprite.flip_x,
            sprite.flip_y
        )

        def sprite_gen() -> Optional[pygame.Surface]:
            return surface_cache.get_surface(
                sprite.image_name,
                sprite.current_frame,
                sprite.frame_count,
                sprite.width,
                sprite.height,
                scale,
                transform.rotation,
                sprite.flip_x,
                sprite.flip_y
            )

        tex = self._get_cached_texture(sprite_key, sprite_gen)
        if not tex:
            return

        state = self._prepare_entity_state(
            camera,
            transform,
            sprite,
            visual_transform,
            alpha,
            tex.width,
            tex.height,
            self.screen.get_rect(),
            scale
        )

        # Override state.rect calculation if needed, but it should be correct as we passed tex.width/height

        if state.is_visible:
            # Draw Shadow
            if state.shadow_props:
                radius_x, radius_y, sx, sy = state.shadow_props
                shadow_key = ("shadow", radius_x, radius_y)
                shadow_gen = self._create_shadow_surface_factory(radius_x, radius_y)
                shadow_tex = self._get_cached_texture(shadow_key, shadow_gen)

                if shadow_tex:
                     self.lights_engine.render_texture(
                        shadow_tex,
                        pl2d.BACKGROUND,
                        pygame.Rect(sx - radius_x, sy - radius_y, radius_x * 2, radius_y * 2),
                        pygame.Rect(0, 0, radius_x * 2, radius_y * 2)
                    )

            # Draw Sprite
            self.lights_engine.render_texture(
                tex,
                pl2d.BACKGROUND,
                state.rect,
                pygame.Rect(0, 0, tex.width, tex.height)
            )

            # Selection
            if is_selected:
                bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)
                self.lights_engine.graphics.render_rectangle(
                    bg_layer,
                    RenderConstants.SELECTION_COLOR_FLOAT,
                    state.rect.center,
                    state.rect.width,
                    state.rect.height,
                    angle=0,
                    antialias=False
                )

    def draw_floating_text(
        self,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ) -> None:
        font = self._get_font(text_comp.size)
        text_surface = font.render(text_comp.text, True, text_comp.color)

        if text_comp.max_lifetime > 0:
            alpha_val = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
            alpha_val = max(0, min(255, alpha_val))
            text_surface.set_alpha(alpha_val)

        tex = self.lights_engine.surface_to_texture(text_surface)

        screen_x, screen_y = camera.world_to_screen(
            transform.x, transform.y, screen_w, screen_h
        )
        rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))

        self.lights_engine.render_texture(
            tex,
            pl2d.FOREGROUND,
            rect,
            pygame.Rect(0, 0, tex.width, tex.height)
        )
        tex.release()
