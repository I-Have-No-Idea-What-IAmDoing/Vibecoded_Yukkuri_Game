"""
Renderer Constants Module.
"""


class RenderConstants:
    """
    Constant values for rendering configuration.
    """

    GRID_SIZE: int = 100
    GRID_COLOR: tuple[int, int, int] = (70, 70, 70)
    GRID_COLOR_FLOAT: tuple[float, float, float, float] = (
        70 / 255,
        70 / 255,
        70 / 255,
        1.0,
    )
    SHADOW_COLOR: tuple[int, int, int, int] = (0, 0, 0, 100)
    SELECTION_COLOR: tuple[int, int, int] = (255, 255, 0)
    SELECTION_COLOR_FLOAT: tuple[float, float, float, float] = (1.0, 1.0, 0.0, 1.0)
    SELECTION_WIDTH: int = 2
    SHADOW_SCALE_X: float = 0.4
    SHADOW_SCALE_Y: float = 0.5
    CIRCLE_OCCLUDER_SEGMENTS: int = 12
