"""
LOD (Level of Detail) System.
"""

from ..ecs import System, World
from ...engine.components import Transform, LODComponent
from ..camera import Camera
from ...engine.protocols import ISpatialService
from .spatial import SpatialSystem


class LODSystem(System):
    run_after = [SpatialSystem]
    """
    System responsible for assigning LOD levels to entities based on distance from camera.
    """

    def __init__(self, enable_lod: bool = True, update_interval: int = 10):
        self.enable_lod = enable_lod
        self.update_interval = update_interval
        self.frame_count = 0
        self.high_dist = 800
        self.med_dist = 1500
        self.active_entities: set[int] = set()

    def update(self, world: World, dt: float) -> None:
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
        spatial_service = world.services.try_get(ISpatialService)

        if not camera:
            return

        if not spatial_service:
            self._update_naive(world, camera.camera_x, camera.camera_y)
            return

        self._update_optimized(world, spatial_service, camera.camera_x, camera.camera_y)

    def _update_optimized(
        self, world: World, spatial_service: ISpatialService, cx: float, cy: float
    ) -> None:
        current_active = set()
        rect_x = cx - self.med_dist
        rect_y = cy - self.med_dist
        rect_w = self.med_dist * 2
        rect_h = self.med_dist * 2

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
                if lod.level != 2:
                    lod.level = 2

        for entity in self.active_entities:
            if entity not in current_active:
                lod = world.try_get_component(entity, LODComponent)
                if lod:
                    lod.level = 2
        self.active_entities = current_active

    def _update_naive(self, world: World, cx: float, cy: float) -> None:
        high_sq = self.high_dist * self.high_dist
        med_sq = self.med_dist * self.med_dist
        for entity, (transform, lod) in world.get_components_tuple(Transform, LODComponent):
            dx = transform.x - cx
            dy = transform.y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq < high_sq:
                lod.level = 0
            elif dist_sq < med_sq:
                lod.level = 1
            else:
                lod.level = 2
