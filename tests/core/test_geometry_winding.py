from unittest.mock import MagicMock

# Ensure we can import modules that might depend on others
# We don't need to mock pygame here as GeometryUtils doesn't use it directly,
# but it uses pymunk.

from yukkuri_game.engine.renderer.geometry_utils import GeometryUtils
from yukkuri_game.game.components import Occluder


def calculate_signed_area(vertices):
    """
    Calculates signed area of polygon.
    Standard Shoelace formula: 0.5 * sum(x_i*y_{i+1} - x_{i+1}*y_i).

    Coordinate System Analysis:
    - Standard Cartesian (Y-up):
        - CCW -> Positive Area
        - CW -> Negative Area
    - Screen Coordinates (Y-down):
        - Y axis is flipped.
        - Visual CCW (e.g. TL -> BL -> BR -> TR) results in NEGATIVE calculated area.
        - Visual CW (e.g. TL -> TR -> BR -> BL) results in POSITIVE calculated area.

    We enforce Visual CCW for correct shadow volumes.
    Thus, we expect Negative Area in this calculation.
    """
    area = 0.0
    for i in range(len(vertices)):
        j = (i + 1) % len(vertices)
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return area / 2.0


class MockTransform:
    x: float
    y: float
    width: float
    height: float
    rotation: float
    scale: float

    def __init__(self):
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.scale = 1.0


def test_box_winding_order():
    """Test that generated box vertices are CCW in screen space (Negative Area)."""
    transform = MockTransform()
    occluder = Occluder()  # Use real component class if simple, or mock if complex
    # Occluder is likely a simple data class or Pydantic model.
    # Let's check if we can instantiate it easily. If not, use MagicMock.

    # Let's inspect Occluder component definition first to be safe,
    # but based on geometry_utils usage, it has .polygon and .static attributes.
    occluder = MagicMock()
    occluder.polygon = None
    occluder.static = False

    # Default box size logic in code:
    # corners = [(-s/2, -s/2), (-s/2, s/2), (s/2, s/2), (s/2, -s/2)]
    # TL -> BL -> BR -> TR

    verts = GeometryUtils.get_occluder_vertices(1, transform, occluder)

    area = calculate_signed_area(verts)
    assert area < 0, f"Box area was {area}, expected negative (Screen CCW)"


def test_sprite_box_winding_order():
    """Test that generated sprite box vertices are CCW in screen space."""
    transform = MockTransform()
    occluder = MagicMock()
    occluder.polygon = None
    occluder.static = False

    sprite = MagicMock()
    sprite.width = 100
    sprite.height = 100

    verts = GeometryUtils.get_occluder_vertices(1, transform, occluder, sprite=sprite)

    area = calculate_signed_area(verts)
    assert area < 0, f"Sprite Box area was {area}, expected negative (Screen CCW)"


def test_circle_winding_order():
    """Test that generated circle vertices are CCW in screen space."""
    # Circle vertices are cached unit circle.
    verts = GeometryUtils.get_circle_vertices()

    # Check unit circle area.
    area = calculate_signed_area(verts)
    assert area < 0, f"Circle area was {area}, expected negative (Screen CCW)"
