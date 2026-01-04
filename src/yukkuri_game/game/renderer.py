"""
Module handling the game world rendering logic.
"""

import pygame
from typing import Optional, List, Tuple, Any, Iterable
from pygame_light2d import LightingEngine
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager
from .components import (
    Transform,
    Sprite,
    Selectable,
    FloatingText,
    PhysicsBody,
    VisualTransform,
    LightSource,
    Occluder,
)
from .camera import Camera
from .surface_cache import SurfaceCache
from .render_backends import RenderBackend, PygameRenderBackend, Light2DRenderBackend
from .systems.sector_system import SectorMap
from .services import TimeService


class WorldRenderer:
    """
    Handles the pure drawing logic for the game world.

    Attributes:
        screen (pygame.Surface): The surface to render to.
        camera (Camera): The world view manager.
        rm (ResourceManager): The resource manager for fetching assets.
        backend (RenderBackend): The rendering backend strategy.
        surface_cache (SurfaceCache): The surface cache.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        camera: Camera,
        resource_manager: ResourceManager,
        lights_engine: Optional[LightingEngine] = None,
        texture_cache_max_size: int = 500,
    ) -> None:
        """
        Initializes the WorldRenderer.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            camera (Camera): The world view manager.
            resource_manager (ResourceManager): The resource manager.
            lights_engine (LightingEngine, optional): The lighting engine instance.
            texture_cache_max_size (int): The maximum number of textures to keep in memory (for Light2D).
        """
        self.screen = screen
        self.camera = camera
        self.rm = resource_manager

        # Initialize Surface Cache
        self.surface_cache = SurfaceCache(self.rm)

        # Initialize Backend
        if lights_engine:
            self.backend: RenderBackend = Light2DRenderBackend(
                lights_engine, screen, texture_cache_max_size
            )
        else:
            self.backend: RenderBackend = PygameRenderBackend(screen)

    def render(self, world: World, alpha: float = 1.0) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        self.backend.clear()

        # Render background grid
        sw, sh = self.screen.get_size()
        self.backend.draw_grid(self.camera, sw, sh)

        # Optimization: Use SectorMap to query only potentially visible entities
        # This reduces the number of entities we iterate, sort, and process for rendering.
        sector_map = world.services.try_get(SectorMap)
        visible_entities = None

        if sector_map:
            # Calculate visible world bounds
            # We use a large buffer (1000.0) to include lights that might be off-screen
            # but casting light onto the screen, and large sprites.
            buffer = 1000.0
            start_x, start_y = self.camera.screen_to_world(0, 0, sw, sh)
            end_x, end_y = self.camera.screen_to_world(sw, sh, sw, sh)

            # Handling zoom and rotation is tricky with simple rect, so we take min/max
            min_x = min(start_x, end_x) - buffer
            min_y = min(start_y, end_y) - buffer
            width = abs(end_x - start_x) + 2 * buffer
            height = abs(end_y - start_y) + 2 * buffer

            visible_entities = sector_map.get_entities_in_rect(
                min_x, min_y, width, height
            )

        # Update Lighting (if backend supports it)
        if isinstance(self.backend, Light2DRenderBackend):
            # Gather Lights
            lights_data = []

            if visible_entities is not None:
                # Filter visible entities for lights
                for ent in visible_entities:
                    if world.has_component(ent, LightSource) and world.has_component(
                        ent, Transform
                    ):
                        lights_data.append(
                            (
                                ent,
                                world.get_component(ent, Transform),
                                world.get_component(ent, LightSource),
                            )
                        )
            else:
                # Fallback to iteration
                for ent, (transform, light) in world.get_components_tuple(
                    Transform, LightSource
                ):
                    lights_data.append((ent, transform, light))

            # Get Time
            time_service = world.services.try_get(TimeService)
            time_elapsed = time_service.time_elapsed if time_service else 0.0

            self.backend.update_lights(lights_data, self.camera, time_elapsed)

            # Gather Occluders
            occluders_data = []
            if visible_entities is not None:
                for ent in visible_entities:
                    if world.has_component(ent, Occluder) and world.has_component(
                        ent, Transform
                    ):
                        transform = world.get_component(ent, Transform)
                        occluder = world.get_component(ent, Occluder)
                        sprite = world.try_get_component(ent, Sprite)
                        body = world.try_get_component(ent, PhysicsBody)
                        occluders_data.append((ent, transform, occluder, sprite, body))
            else:
                for ent, (transform, occluder) in world.get_components_tuple(
                    Transform, Occluder
                ):
                    # Optionally get Sprite and PhysicsBody for fallback shape
                    sprite = world.try_get_component(ent, Sprite)
                    body = world.try_get_component(ent, PhysicsBody)
                    occluders_data.append((ent, transform, occluder, sprite, body))

            self.backend.update_occluders(occluders_data, self.camera)

        # Render entities
        render_data: List[Tuple[int, Tuple[Any, ...]]] = []

        if visible_entities is not None:
            # Optimize: Only fetch components for visible entities
            for ent in visible_entities:
                # We need Transform, Sprite, VisualTransform
                # Check presence efficiently
                transform = world.try_get_component(ent, Transform)
                if not transform:
                    continue

                sprite = world.try_get_component(ent, Sprite)
                if not sprite:
                    continue

                visual_transform = world.try_get_component(ent, VisualTransform)
                if not visual_transform:
                    continue

                render_data.append((ent, (transform, sprite, visual_transform)))
        else:
            # Fallback: Iterate all entities with these components
            # Use get_components_tuple for efficient retrieval
            render_data = world.get_components_tuple(Transform, Sprite, VisualTransform)

        # Sort by Transform.y for depth (ground position).
        # Data structure: [(entity_id, (transform, sprite, visual_transform)), ...]
        # x[1] is the tuple of components, x[1][0] is Transform
        render_data.sort(key=lambda x: x[1][0].y)

        for ent, (transform, sprite, visual_transform) in render_data:
            self._render_entity(world, ent, transform, sprite, visual_transform, alpha)

        # Render Floating Text
        self._render_floating_text(world, sw, sh, visible_entities)

    def _render_entity(
        self,
        world: World,
        ent: int,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        alpha: float,
    ) -> None:
        """
        Prepares and delegates entity rendering to the backend.

        Args:
            world (World): The ECS World.
            ent (int): Entity ID.
            transform (Transform): The transform component.
            sprite (Sprite): The sprite component.
            visual_transform (VisualTransform): The visual transform component.
            alpha (float): Interpolation factor.
        """
        # Selectable is optional
        selectable = world.try_get_component(ent, Selectable)
        is_selected = selectable.selected if selectable else False

        self.backend.draw_entity(
            self.camera,
            self.surface_cache,
            transform,
            sprite,
            visual_transform,
            is_selected,
            alpha,
        )

    def _render_floating_text(
        self,
        world: World,
        sw: int,
        sh: int,
        visible_entities: Optional[Iterable[int]] = None,
    ) -> None:
        """
        Renders floating text entities.

        Args:
            world (World): The ECS World.
            sw (int): Screen width.
            sh (int): Screen height.
            visible_entities (Optional[Iterable[int]]): Iterable of visible entity IDs.
        """
        if visible_entities is not None:
            for ent in visible_entities:
                transform = world.try_get_component(ent, Transform)
                text_comp = world.try_get_component(ent, FloatingText)
                if transform and text_comp:
                    self.backend.draw_floating_text(
                        self.camera, transform, text_comp, sw, sh
                    )
        else:
            for entity, (transform, text_comp) in world.get_components_tuple(
                Transform, FloatingText
            ):
                self.backend.draw_floating_text(
                    self.camera, transform, text_comp, sw, sh
                )

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """
        Toggles lighting debug mode.
        If enabled, sets ambient light to full white for visibility.
        If disabled, it should revert to normal (DayNightSystem will handle next frame).

        Args:
            enabled (bool): Whether debug mode is enabled.
        """
        if isinstance(self.backend, Light2DRenderBackend):
            if enabled:
                self.backend.set_ambient_light((255, 255, 255, 255))
            # Else: nothing, next frame update will overwrite ambient
