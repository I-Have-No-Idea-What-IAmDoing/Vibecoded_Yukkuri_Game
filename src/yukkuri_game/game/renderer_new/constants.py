from typing import Tuple


class RenderConstants:
    GRID_SIZE: int = 100
    GRID_COLOR: Tuple[int, int, int] = (80, 80, 80)
    GRID_COLOR_FLOAT: Tuple[float, float, float, float] = (
        80 / 255,
        80 / 255,
        80 / 255,
        1.0,
    )
    SHADOW_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 100)
    SELECTION_COLOR: Tuple[int, int, int] = (255, 255, 0)
    SELECTION_COLOR_FLOAT: Tuple[float, float, float, float] = (1.0, 1.0, 0.0, 1.0)
    SELECTION_WIDTH: int = 2
    SHADOW_SCALE_X: float = 0.4
    SHADOW_SCALE_Y: float = 0.5
    CIRCLE_OCCLUDER_SEGMENTS: int = 12
