"""
AI Debug Renderer.
Provides debug visualization for the Utility AI and Behavior system.
"""

from typing import TYPE_CHECKING

import pygame

from ..components import AIState, Blackboard, MoveCommand
from yukkuri_game.engine.components import Transform

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
        from yukkuri_game.engine.camera import Camera
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
        """Draws overhead statuses, colliders, destinations, and target lines."""
        from yukkuri_game.engine.components import PhysicsBody
        from yukkuri_game.game.components import SteeringComponent

        current_time = world.time

        for ent, (transform, ai_state) in world.get_components_tuple(
            Transform, AIState
        ):
            start_pos = (transform.x, transform.y)
            sx_start, sy_start = self._world_to_screen(*start_pos)

            # 1. Gather Overhead Diagnostic Details
            action_name = ai_state.current_action or "Idle"

            # Stuck details
            steering = world.try_get_component(ent, SteeringComponent)
            stuck_str = ""
            if steering and steering.time_stuck > 0.1:
                stuck_str = f" [STUCK: {steering.time_stuck:.1f}s]"

            # Pathfinding details
            pathing_str = ""
            state_data = ai_state.state_data or {}
            if state_data.get("path_requesting"):
                pathing_str = " [PATHING...]"

            # Cooldown details
            cooldown_str = ""
            cooldowns = getattr(ai_state, "action_cooldowns", None)
            if cooldowns and action_name in cooldowns:
                expire_time = cooldowns[action_name]
                if current_time < expire_time:
                    remaining = expire_time - current_time
                    cooldown_str = f" [COOLDOWN: {remaining:.1f}s]"

            # Compile text label
            text_color = (255, 50, 50) if stuck_str else self.COLOR_TEXT
            status_text = self.font.render(
                f"{action_name}{stuck_str}{pathing_str}{cooldown_str}",
                True,
                text_color,
            )
            # Render centered above Yukkuri head (approx 45px offset)
            surface.blit(
                status_text,
                (sx_start - status_text.get_width() // 2, sy_start - 45),
            )

            # 2. Draw physical collision circle
            phys = world.try_get_component(ent, PhysicsBody)
            if phys:
                for shape in phys.body.shapes:
                    if (
                        not shape.sensor
                        and hasattr(shape, "radius")
                        and shape.radius > 0
                    ):
                        screen_radius = int(shape.radius * self.camera.zoom)
                        pygame.draw.circle(
                            surface,
                            (0, 255, 100, 100),
                            (sx_start, sy_start),
                            screen_radius,
                            1,
                        )
                        break

            # 3. Draw World Target Crosshair (Vibrant Magenta)
            if state_data and "path_destination" in state_data:
                dest_x, dest_y = state_data["path_destination"]
                sx_dest, sy_dest = self._world_to_screen(dest_x, dest_y)

                # Draw thin magenta line to ultimate destination
                pygame.draw.line(
                    surface,
                    (255, 0, 255),
                    (sx_start, sy_start),
                    (sx_dest, sy_dest),
                    1,
                )
                # Draw destination target crosshair
                pygame.draw.circle(
                    surface, (255, 0, 255), (sx_dest, sy_dest), 6, 1
                )
                pygame.draw.circle(
                    surface, (255, 0, 255), (sx_dest, sy_dest), 2, 0
                )

            # 4. Draw Line to Target Entity (original logic)
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
                        f"Target: {ai_state.current_target_id}",
                        True,
                        self.COLOR_TEXT,
                    )
                    surface.blit(text, (sx_start + 10, sy_start - 20))

            # 5. Draw MoveCommand Destination OR Path Waypoint (original logic)
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

            # 6. Draw Social Context (original logic)
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
