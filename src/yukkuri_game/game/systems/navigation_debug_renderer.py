"""
Navigation Debug Renderer.
Provides debug visualization for the HPA* navigation system.
"""

from typing import TYPE_CHECKING

import pygame

from ..ai.navigation_constants import TraversalCapability

if TYPE_CHECKING:
    from ...engine.ecs import World


class NavigationDebugRenderer:
    """
    Renders debug visualizations for navigation:
    - Cluster boundaries (green grid)
    - Entrance connections (blue lines between cluster nodes)
    - Active paths (yellow lines)
    - Steering vectors (red rays from entities)
    """

    def __init__(self, world: "World"):
        from ..ai.navigation_service import NavigationService
        from ..camera import Camera
        self.nav_service = world.services.get(NavigationService)
        self.camera = world.services.get(Camera)
        self.enabled = False

        # Colors
        self.COLOR_CLUSTER_BORDER = (0, 200, 0, 100)  # Green, semi-transparent
        self.COLOR_ENTRANCE_WALK = (0, 100, 255, 150)  # Blue (WALK graph)
        self.COLOR_ENTRANCE_FLY = (0, 255, 200, 150)  # Cyan (FLY graph)
        self.COLOR_PATH = (255, 255, 0, 200)  # Yellow
        self.COLOR_STEERING = (255, 50, 50, 200)  # Red

        # Display options
        self.show_fly_graph = False  # Toggle to also show FLY graph

    def toggle(self) -> None:
        """Toggles debug rendering on/off."""
        self.enabled = not self.enabled

    def render(self, surface: pygame.Surface, world: "World") -> None:
        """
        Renders all navigation debug visuals.
        Call this after the main render pass.
        """
        if not self.enabled:
            return

        self._draw_cluster_boundaries(surface)
        self._draw_entrances(
            surface, TraversalCapability.WALK, self.COLOR_ENTRANCE_WALK
        )
        if self.show_fly_graph:
            self._draw_entrances(
                surface, TraversalCapability.FLY, self.COLOR_ENTRANCE_FLY
            )
        self._draw_active_paths(surface, world)
        self._draw_steering_vectors(surface, world)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Converts world coordinates to screen coordinates."""
        sx = wx - self.camera.camera_x + self.camera.width / 2
        sy = wy - self.camera.camera_y + self.camera.height / 2
        return (int(sx), int(sy))

    def _draw_cluster_boundaries(self, surface: pygame.Surface) -> None:
        """Draws green lines for cluster boundaries."""
        from ..ai.hpa import CLUSTER_SIZE

        cell_size = self.nav_service.grid_step_size
        cluster_pixel_size = CLUSTER_SIZE * cell_size

        # Calculate visible area
        cam_x, cam_y = self.camera.camera_x, self.camera.camera_y
        half_w, half_h = self.camera.width / 2, self.camera.height / 2

        left = cam_x - half_w
        right = cam_x + half_w
        top = cam_y - half_h
        bottom = cam_y + half_h

        # Draw vertical lines
        start_cx = int(left // cluster_pixel_size)
        end_cx = int(right // cluster_pixel_size) + 1

        for cx in range(start_cx, end_cx + 1):
            world_x = cx * cluster_pixel_size
            sx, sy_top = self._world_to_screen(world_x, top)
            _, sy_bottom = self._world_to_screen(world_x, bottom)
            pygame.draw.line(
                surface, self.COLOR_CLUSTER_BORDER[:3], (sx, sy_top), (sx, sy_bottom), 1
            )

        # Draw horizontal lines
        start_cy = int(top // cluster_pixel_size)
        end_cy = int(bottom // cluster_pixel_size) + 1

        for cy in range(start_cy, end_cy + 1):
            world_y = cy * cluster_pixel_size
            sx_left, sy = self._world_to_screen(left, world_y)
            sx_right, _ = self._world_to_screen(right, world_y)
            pygame.draw.line(
                surface, self.COLOR_CLUSTER_BORDER[:3], (sx_left, sy), (sx_right, sy), 1
            )

    def _draw_entrances(
        self,
        surface: pygame.Surface,
        capability: int,
        color: tuple[int, int, int, int],
    ) -> None:
        """Draws circles at entrance nodes and lines for edges for the given capability."""
        cell_size = self.nav_service.grid_step_size
        graph = self.nav_service.get_graph(capability)

        # Draw nodes as small circles
        for node_id, node in graph.graph_nodes.items():
            if node_id.startswith("temp_"):
                continue  # Skip temporary nodes

            world_x = node.position[0] * cell_size
            world_y = node.position[1] * cell_size
            sx, sy = self._world_to_screen(world_x, world_y)

            if 0 <= sx < self.camera.width and 0 <= sy < self.camera.height:
                pygame.draw.circle(surface, color[:3], (sx, sy), 4)

        # Draw edges as lines (only draw each edge once)
        drawn_edges = set()
        for node_id, node in graph.graph_nodes.items():
            if node_id.startswith("temp_"):
                continue

            for edge in node.edges:
                edge_key = tuple(sorted([node_id, edge.target_node_id]))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)

                target_node = graph.graph_nodes.get(edge.target_node_id)
                if not target_node or target_node.id.startswith("temp_"):
                    continue

                x1 = node.position[0] * cell_size
                y1 = node.position[1] * cell_size
                x2 = target_node.position[0] * cell_size
                y2 = target_node.position[1] * cell_size

                sx1, sy1 = self._world_to_screen(x1, y1)
                sx2, sy2 = self._world_to_screen(x2, y2)

                pygame.draw.line(surface, color[:3], (sx1, sy1), (sx2, sy2), 1)

    def _draw_active_paths(self, surface: pygame.Surface, world: "World") -> None:
        """Draws yellow lines for active AI paths."""
        from ..components import AIState, Transform

        for ent, (transform, ai_state) in world.get_components_tuple(
            Transform, AIState
        ):
            path = ai_state.path
            if not path or len(path) < 2:
                continue

            # Draw path as connected lines
            points = []
            for waypoint in path:
                sx, sy = self._world_to_screen(waypoint[0], waypoint[1])
                points.append((sx, sy))

            # Also include current position
            current_sx, current_sy = self._world_to_screen(transform.x, transform.y)
            all_points = [(current_sx, current_sy)] + points

            if len(all_points) >= 2:
                pygame.draw.lines(surface, self.COLOR_PATH[:3], False, all_points, 2)

                # Draw a circle at the destination
                if points:
                    pygame.draw.circle(surface, self.COLOR_PATH[:3], points[-1], 6, 2)

    def _draw_steering_vectors(self, surface: pygame.Surface, world: "World") -> None:
        """Draws red arrows for steering forces."""
        from ..components import MovementController, SteeringComponent, Transform

        for ent, (transform, movement, steering) in world.get_components_tuple(
            Transform, MovementController, SteeringComponent
        ):
            # Draw target velocity as an arrow
            vx = movement.target_velocity[0]
            vy = movement.target_velocity[1]

            # Only draw if there's meaningful velocity
            if abs(vx) < 1 and abs(vy) < 1:
                continue

            start_x, start_y = self._world_to_screen(transform.x, transform.y)

            # Scale velocity for visibility (e.g., 0.5 = half actual length)
            scale = 0.5
            end_x = int(start_x + vx * scale)
            end_y = int(start_y + vy * scale)

            pygame.draw.line(
                surface, self.COLOR_STEERING[:3], (start_x, start_y), (end_x, end_y), 2
            )

            # Draw arrowhead
            pygame.draw.circle(surface, self.COLOR_STEERING[:3], (end_x, end_y), 3)
