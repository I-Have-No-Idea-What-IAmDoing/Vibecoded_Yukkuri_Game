"""
AI Debug Renderer.
Provides debug visualization for the Utility AI and Behavior system.
"""

from typing import TYPE_CHECKING

import pygame

from ..components import AIState, Blackboard, MoveCommand, Transform

if TYPE_CHECKING:
    from ...engine.ecs import World


class AIDebugRenderer:
    """
    Renders debug visualizations for AI:
    - Line to current target (Yellow)
    - MoveCommand destination (Magenta)
    - Social Context lines (Green=Friend, Red=Enemy)
    """

    def __init__(self, world: "World"):
        """
        Initializes the AIDebugRenderer.

        Args:
            world (World): The ECS World instance to fetch services from.
        """
        from ..camera import Camera
        self.camera = world.services.get(Camera)
        self.enabled = False
        self.font = pygame.font.SysFont("Arial", 12)

        # Colors
        self.COLOR_TARGET_LINE = (255, 255, 0, 150)  # Yellow
        self.COLOR_MOVE_CMD = (0, 255, 255, 150)  # Cyan
        self.COLOR_FRIEND = (0, 255, 0, 100)  # Green
        self.COLOR_ENEMY = (255, 0, 0, 100)  # Red
        self.COLOR_NEUTRAL = (200, 200, 200, 100)  # Gray
        self.COLOR_TEXT = (255, 255, 255)  # White

    def toggle(self) -> None:
        """Toggles debug rendering on/off."""
        self.enabled = not self.enabled

    def render(self, surface: pygame.Surface, world: "World") -> None:
        """
        Renders all AI debug visuals.

        Call this after the main render pass.

        Args:
            surface (pygame.Surface): The surface to draw on.
            world (World): The ECS World.
        """
        if not self.enabled:
            return

        self._draw_ai_interactions(surface, world)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Converts world coordinates to screen coordinates."""
        sx, sy = self.camera.world_to_screen_fast(wx, wy)
        return (int(sx), int(sy))

    def _draw_ai_interactions(self, surface: pygame.Surface, world: "World") -> None:
        for ent, (transform, ai_state) in world.get_components_tuple(
            Transform, AIState
        ):
            start_pos = (transform.x, transform.y)
            sx_start, sy_start = self._world_to_screen(*start_pos)

            # 1. Draw Line to Target Entity
            if ai_state.current_target_id != -1:
                target_trans = world.try_get_component(
                    ai_state.current_target_id, Transform
                )
                if target_trans:
                    sx_end, sy_end = self._world_to_screen(
                        target_trans.x, target_trans.y
                    )
                    pygame.draw.line(
                        surface,
                        self.COLOR_TARGET_LINE[:3],
                        (sx_start, sy_start),
                        (sx_end, sy_end),
                        1,
                    )

                    # Draw "Target: [ID]" text
                    text = self.font.render(
                        f"Target: {ai_state.current_target_id}", True, self.COLOR_TEXT
                    )
                    surface.blit(text, (sx_start + 10, sy_start - 20))

            # 2. Draw MoveCommand Destination OR Path Waypoint
            move_cmd = world.try_get_component(ent, MoveCommand)
            if move_cmd:
                mx, my = move_cmd.target_pos
                sx_move, sy_move = self._world_to_screen(mx, my)
                pygame.draw.line(
                    surface,
                    self.COLOR_MOVE_CMD[:3],
                    (sx_start, sy_start),
                    (sx_move, sy_move),
                    2,
                )
                pygame.draw.circle(
                    surface, self.COLOR_MOVE_CMD[:3], (sx_move, sy_move), 3
                )
            elif ai_state.path and len(ai_state.path) > 0:
                # Visualize next waypoint if following path
                px, py = ai_state.path[0]
                sx_path, sy_path = self._world_to_screen(px, py)
                # Use same color/style as MoveCommand (Cyan)
                pygame.draw.line(
                    surface,
                    self.COLOR_MOVE_CMD[:3],
                    (sx_start, sy_start),
                    (sx_path, sy_path),
                    2,
                )
                pygame.draw.circle(
                    surface, self.COLOR_MOVE_CMD[:3], (sx_path, sy_path), 3
                )

            # 3. Draw Social Context (from Blackboard)
            blackboard = world.try_get_component(ent, Blackboard)
            if blackboard and blackboard.visible_targets:
                for target_id, info in blackboard.visible_targets.items():
                    t_trans = world.try_get_component(target_id, Transform)
                    if t_trans:
                        ex, ey = self._world_to_screen(t_trans.x, t_trans.y)
                        color = self.COLOR_NEUTRAL[:3]

                        if info.relation == "Friend":
                            color = self.COLOR_FRIEND[:3]
                        elif info.relation in ("Enemy", "Threat", "Prey"):
                            color = self.COLOR_ENEMY[:3]

                        pygame.draw.line(
                            surface, color, (sx_start, sy_start), (ex, ey), 1
                        )
