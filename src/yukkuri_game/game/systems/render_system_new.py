"""
New Render System Module.
"""

import pygame
import math
from loguru import logger
from typing import Optional, List, Tuple
from pygame_light2d import LightingEngine

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
    FlickerStyle
)
from ..systems.sector_system import SectorMap, OccluderMap
from ..services import TimeService
from ..surface_cache import SurfaceCache

from ..renderer_new.renderer import Renderer
from ..renderer_new.backend import RenderBackend
from ..renderer_new.pygame_backend import PygameBackend
from ..renderer_new.light2d_backend import Light2DBackend
from ..renderer_new.geometry_utils import GeometryUtils
from ..renderer_new.commands import (
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
    RenderCommand
)
from ..renderer_new.constants import RenderConstants

# Layers
LAYER_BACKGROUND = 0
LAYER_SHADOWS = 1
LAYER_ENTITIES = 2
LAYER_EFFECTS = 3
LAYER_UI = 10

class NewRenderSystem(System):
    """
    System responsible for rendering using the new architecture.
    """

    def __init__(
        self, screen: pygame.Surface, world: World, lights_engine: Optional[LightingEngine] = None
    ):
        self.screen = screen
        self.rm = world.services.get(ResourceManager)
        self.camera = world.services.get(Camera)
        self.surface_cache = SurfaceCache(self.rm)

        backend: RenderBackend
        if lights_engine:
            backend = Light2DBackend(screen, lights_engine)
        else:
            backend = PygameBackend(screen)

        self.renderer = Renderer(backend)
        self.lights_enabled = lights_engine is not None

    def update(self, world: World, alpha: float) -> None:
        """
        Main render loop.
        """
        sw, sh = self.screen.get_size()

        # If using lighting engine with scaling, use native resolution for camera calculations
        if self.lights_enabled:
             # Try to get native resolution from engine (internal attribute)
             engine = self.renderer.backend.engine
             if hasattr(engine, '_native_res'):
                 sw, sh = engine._native_res

        self.camera.update_matrices(sw, sh)

        self.renderer.clear_screen((30, 30, 30)) # Dark background

        # 1. Grid (Optional, maybe make it a command or specialized draw)
        self._draw_grid(sw, sh)

        # 2. Query Visible Entities
        visible_entities = self._get_visible_entities(world, sw, sh)

        # 3. Process Entities
        for ent in visible_entities:
            self._process_entity(world, ent, alpha, sw, sh)

        # 4. Floating Text
        self._process_floating_text(world, sw, sh, alpha)

        # 5. Render
        self.renderer.render()

    def _get_visible_entities(self, world: World, sw: int, sh: int) -> List[int]:
        sector_map = world.services.try_get(SectorMap)
        if sector_map:
            buffer = 500.0
            start_x, start_y = self.camera.screen_to_world(0, 0, sw, sh)
            end_x, end_y = self.camera.screen_to_world(sw, sh, sw, sh)

            min_x = min(start_x, end_x) - buffer
            min_y = min(start_y, end_y) - buffer
            width = abs(end_x - start_x) + 2 * buffer
            height = abs(end_y - start_y) + 2 * buffer

            return sector_map.get_entities_in_rect(min_x, min_y, width, height)
        else:
            # Fallback
            return [e for e, _ in world.get_components_tuple(Transform)]

    def _draw_grid(self, sw: int, sh: int) -> None:
        # Generate grid lines commands? Or just draw immediate if backend supports it.
        # Let's verify backend has draw_line

        grid_size = RenderConstants.GRID_SIZE
        color = RenderConstants.GRID_COLOR

        start_col, end_col, start_row, end_row = self._calculate_grid_bounds(sw, sh, grid_size)

        for col in range(start_col, end_col):
            x = col * grid_size
            sx, _ = self.camera.world_to_screen_fast(x, 0)
            self.renderer.backend.draw_line((sx, 0), (sx, sh), color)

        for row in range(start_row, end_row):
            y = row * grid_size
            _, sy = self.camera.world_to_screen_fast(0, y)
            self.renderer.backend.draw_line((0, sy), (sw, sy), color)

    def _calculate_grid_bounds(self, screen_w: int, screen_h: int, grid_size: int):
        start_x, start_y = self.camera.screen_to_world(0, 0, screen_w, screen_h)
        end_x, end_y = self.camera.screen_to_world(screen_w, screen_h, screen_w, screen_h)

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1
        return start_col, end_col, start_row, end_row

    def _process_entity(self, world: World, ent: int, alpha: float, sw: int, sh: int) -> None:
        transform = world.try_get_component(ent, Transform)
        if not transform: return

        # Interpolation
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
            scale = transform.scale * self.camera.zoom

            # Shadow
            # Calculate shadow position
            shadow_x, shadow_y = self.camera.world_to_screen_fast(
                ix + visual.shadow_position.x,
                iy + visual.shadow_position.y
            )

            shadow_radius_x = sprite.width * scale * RenderConstants.SHADOW_SCALE_X
            shadow_radius_y = shadow_radius_x * RenderConstants.SHADOW_SCALE_Y

            if shadow_radius_x > 0:
                self.renderer.submit(ShadowCommand(
                    layer=LAYER_SHADOWS,
                    z_index=iy, # Shadow sorts with entity
                    position=(shadow_x, shadow_y),
                    radius=(shadow_radius_x, shadow_radius_y)
                ))

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
                sprite.flip_y
            )

            if img:
                selectable = world.try_get_component(ent, Selectable)
                is_selected = selectable.selected if selectable else False

                # Apply vertical offset
                sprite_sy = screen_pos[1] - (visual.vertical_offset * self.camera.zoom)

                # Construct cache key for texture cache in Light2DBackend
                # Must match what uniquely identifies the visual appearance
                cache_key = (
                    sprite.image_name,
                    sprite.current_frame,
                    round(scale, 3), # Round to reduce cache thrashing
                    round(transform.rotation, 1),
                    sprite.flip_x,
                    sprite.flip_y
                )

                self.renderer.submit(SpriteCommand(
                    layer=LAYER_ENTITIES,
                    z_index=iy,
                    image=img,
                    position=(screen_pos[0], sprite_sy),
                    selected=is_selected,
                    alpha=255, # TODO: Support transparency in component
                    cache_key=cache_key
                ))

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

                self.renderer.submit(LightCommand(
                    layer=LAYER_EFFECTS, # Lights are handled specially by backend
                    z_index=iy,
                    entity_id=ent,
                    position=screen_pos,
                    radius=radius,
                    color=color,
                    intensity=intensity,
                    flicker_style=light.flicker_style
                ))

            occluder = world.try_get_component(ent, Occluder)
            if occluder:
                self._process_occluder(world, ent, transform, occluder)

    def _process_occluder(self, world: World, ent: int, transform: Transform, occluder: Occluder):
        sprite = world.try_get_component(ent, Sprite)
        body = world.try_get_component(ent, PhysicsBody)

        world_verts = GeometryUtils.get_occluder_vertices(ent, transform, occluder, sprite, body)

        if len(world_verts) < 3:
            return

        screen_verts = []
        for wx, wy in world_verts:
            sx, sy = self.camera.world_to_screen_fast(wx, wy)
            screen_verts.append((sx, sy))

        self.renderer.submit(OccluderCommand(
            layer=LAYER_BACKGROUND,
            z_index=0,
            entity_id=ent,
            vertices=screen_verts
        ))

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        self.renderer.set_ambient_light(color)

    def _process_floating_text(self, world: World, sw: int, sh: int, alpha: float) -> None:
        # Iterate all FloatingText
        # Optimize: visible only?
        for ent, (transform, text) in world.get_components_tuple(Transform, FloatingText):
            sx, sy = self.camera.world_to_screen_fast(transform.x, transform.y)

            # Cull if offscreen?
            if 0 <= sx <= sw and 0 <= sy <= sh:
                alpha_val = 255
                if text.max_lifetime > 0:
                    alpha_val = int(255 * (text.lifetime / text.max_lifetime))

                self.renderer.submit(TextCommand(
                    layer=LAYER_UI,
                    z_index=transform.y + 1000, # On top
                    text=text.text,
                    position=(sx, sy),
                    size=text.size,
                    color=text.color,
                    alpha=alpha_val
                ))
