"""
Module defining the LOD (Level of Detail) System.
"""

from ...engine.ecs import System, World
from ..components import Transform, LODComponent
from ..camera import Camera
from .spatial_system import SpatialService


class LODSystem(System):
    """
    System responsible for assigning LOD levels to entities based on distance from camera.

    LOD Levels:
    0: High (Priority)
    1: Medium
    2: Low
    3: Culled (Too far)
    """

    def __init__(self, enable_lod: bool = True, update_interval: int = 10):
        """
        Args:
            enable_lod (bool): If False, all entities stay at High LOD (deterministic for tests).
            update_interval (int): Number of frames between LOD recalculations.
        """
        self.enable_lod = enable_lod
        self.update_interval = update_interval
        self.frame_count = 0

        # Ranges
        self.high_dist = 800
        self.med_dist = 1500
        # self.high_dist_sq = 800 * 800
        # self.med_dist_sq = 1500 * 1500

        # State tracking for optimization
        # We track entities that were High/Med last frame so we can downgrade them if they leave range
        self.active_entities: set[int] = set()

    def update(self, world: World, dt: float) -> None:
        """
        Updates LOD levels for all entities.
        """
        # If disabled: Force all to High (0) for determinism.
        if not self.enable_lod:
            for entity, (_, lod) in world.get_components_tuple(Transform, LODComponent):
                if lod.level != 0:
                    lod.level = 0
            return

        self.frame_count += 1
        if self.frame_count < self.update_interval:
            return

        self.frame_count = 0

        camera = world.services.try_get(Camera)
        spatial_service = world.services.try_get(SpatialService)

        if not camera:
            return

        # Optimization: Use SpatialService to only query entities in visual range
        if not spatial_service:
            # Fallback to O(N) if no SpatialService
            self._update_naive(world, camera.camera_x, camera.camera_y)
            return

        self._update_optimized(world, spatial_service, camera.camera_x, camera.camera_y)

    def _update_optimized(
        self, world: World, spatial_service: SpatialService, cx: float, cy: float
    ) -> None:
        """
        Optimized update using Spatial Partitioning.
        O(Visible Entities) + O(Entities leaving view).
        """
        current_active = set()

        # define view rect for "Medium" range (max interest)
        # 1500 padding around camera
        rect_x = cx - self.med_dist
        rect_y = cy - self.med_dist
        rect_w = self.med_dist * 2
        rect_h = self.med_dist * 2

        # Get potential entities from SpatialService
        visible_ids = spatial_service.get_entities_in_rect(rect_x, rect_y, rect_w, rect_h)

        high_dist_sq = self.high_dist * self.high_dist
        med_dist_sq = self.med_dist * self.med_dist

        for entity in visible_ids:
            lod = world.try_get_component(entity, LODComponent)
            if not lod:
                continue

            transform = world.try_get_component(entity, Transform)
            if not transform:
                continue

            dx = transform.x - cx
            dy = transform.y - cy
            dist_sq = dx * dx + dy * dy

            if dist_sq < high_dist_sq:
                lod.level = 0
                current_active.add(entity)
            elif dist_sq < med_dist_sq:
                lod.level = 1
                current_active.add(entity)
            else:
                # In sector query but physically outside circle radius (corners of rect)
                # Should be Low
                if lod.level != 2:
                    lod.level = 2

        # Downgrade entities that left the active range.
        for entity in self.active_entities:
            if entity not in current_active:
                lod = world.try_get_component(entity, LODComponent)
                if lod:
                    lod.level = 2

        self.active_entities = current_active

    def _update_naive(self, world: World, cx: float, cy: float) -> None:
        """Fallback O(N) update."""
        high_sq = self.high_dist * self.high_dist
        med_sq = self.med_dist * self.med_dist

        for entity, (transform, lod) in world.get_components_tuple(
            Transform, LODComponent
        ):
            dx = transform.x - cx
            dy = transform.y - cy
            dist_sq = dx * dx + dy * dy

            if dist_sq < high_sq:
                lod.level = 0
            elif dist_sq < med_sq:
                lod.level = 1
            else:
                lod.level = 2
