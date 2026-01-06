from typing import Tuple


class RenderConstants:
    GRID_SIZE: int = 100
    GRID_COLOR: Tuple[int, int, int] = (50, 50, 50)
    GRID_COLOR_FLOAT: Tuple[float, float, float, float] = (
        50 / 255,
        50 / 255,
        50 / 255,
        1.0,
    )
    SHADOW_COLOR: Tuple[int, int, int, int] = (0, 0, 0, 100)
    SELECTION_COLOR: Tuple[int, int, int] = (255, 255, 0)
    SELECTION_COLOR_FLOAT: Tuple[float, float, float, float] = (1.0, 1.0, 0.0, 1.0)
    SELECTION_WIDTH: int = 2
    SHADOW_SCALE_X: float = 0.4
    SHADOW_SCALE_Y: float = 0.5
    CIRCLE_OCCLUDER_SEGMENTS: int = 12
