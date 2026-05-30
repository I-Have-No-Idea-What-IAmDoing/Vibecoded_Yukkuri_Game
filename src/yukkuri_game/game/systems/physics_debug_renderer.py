"""Physics Debug Renderer.

Provides debug visualization for Pymunk collision shapes and hitboxes.
"""

from typing import TYPE_CHECKING

import pygame
import pymunk

from ...engine.camera import Camera
from ...engine.components import PhysicsBody

if TYPE_CHECKING:
    from ...engine.ecs import World


class PhysicsDebugRenderer:
    """Renders debug visualizations for collision shapes and hitboxes:

    - Sensors/triggers: Cyan (0, 255, 255)
    - Static bodies/boundaries: Orange/Red (255, 69, 0)
    - Dynamic bodies: Green (0, 255, 0)
    """

    def __init__(self, world: "World") -> None:
        """Initializes the PhysicsDebugRenderer.

        Args:
            world (World): The ECS World instance.
        """
        self.camera: Camera = world.services.get(Camera)
        self.enabled: bool = False
        self.COLOR_DYNAMIC: tuple[int, int, int] = (0, 255, 0)  # Green
        self.COLOR_STATIC: tuple[int, int, int] = (255, 69, 0)  # Orange/Red
        self.COLOR_SENSOR: tuple[int, int, int] = (0, 255, 255)  # Cyan

    def toggle(self) -> None:
        """Toggles debug rendering on/off."""
        self.enabled = not self.enabled

    def render(self, surface: pygame.Surface, world: "World") -> None:
        """Renders all collision shapes.

        Call this after the main render pass.

        Args:
            surface (pygame.Surface): The screen surface to draw on.
            world (World): The ECS World instance.
        """
        if not self.enabled:
            return

        for entity, pbody in world.get_components(PhysicsBody).items():
            if not pbody.body or not pbody.shape:
                continue

            shape = pbody.shape

            # Choose color based on role
            if shape.sensor:
                color = self.COLOR_SENSOR
            elif pbody.body.body_type == pymunk.Body.STATIC:
                color = self.COLOR_STATIC
            else:
                color = self.COLOR_DYNAMIC

            if isinstance(shape, pymunk.Circle):
                # Draw circle shape
                pos = pbody.body.position + shape.offset
                sx, sy = self._world_to_screen(pos.x, pos.y)
                radius = shape.radius
                pygame.draw.circle(
                    surface, color, (sx, sy), int(radius), 1
                )
                # Draw a line from center to edge to show rotation
                angle = pbody.body.angle
                edge_pos = pos + pymunk.vec2d.Vec2d(radius, 0).rotated(angle)
                esx, esy = self._world_to_screen(edge_pos.x, edge_pos.y)
                pygame.draw.line(
                    surface, color, (sx, sy), (esx, esy), 1
                )

            elif isinstance(shape, pymunk.Segment):
                # Draw segment shape
                a = pbody.body.position + shape.a.rotated(pbody.body.angle)
                b = pbody.body.position + shape.b.rotated(pbody.body.angle)
                sx1, sy1 = self._world_to_screen(a.x, a.y)
                sx2, sy2 = self._world_to_screen(b.x, b.y)
                pygame.draw.line(
                    surface, color, (sx1, sy1), (sx2, sy2), 1
                )

            elif isinstance(shape, pymunk.Poly):
                # Draw polygon shape
                vertices = []
                for v in shape.get_vertices():
                    pos = pbody.body.position + v.rotated(pbody.body.angle)
                    sx, sy = self._world_to_screen(pos.x, pos.y)
                    vertices.append((sx, sy))
                if len(vertices) >= 3:
                    pygame.draw.polygon(
                        surface, color, vertices, 1
                    )

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Converts world coordinates to screen coordinates.

        Args:
            wx (float): World X coordinate.
            wy (float): World Y coordinate.

        Returns:
            tuple[int, int]: The screen coordinates.
        """
        sx = wx - self.camera.camera_x + self.camera.width / 2
        sy = wy - self.camera.camera_y + self.camera.height / 2
        return (int(sx), int(sy))
