"""
Collision Category Constants.
"""


class CollisionCategories:
    """
    Bitmask categories for Pymunk collision filtering.

    Attributes:
        GROUND_UNIT (int): Category for ground-based entities (Yukkuris walking).
        FLYING_UNIT (int): Category for flying entities.
        ITEM (int): Category for Item entities.
        LOW_OBSTACLE (int): Category for low obstacles (fences, toys).
        HIGH_OBSTACLE (int): Category for high obstacles (walls, buildings).
        WATER (int): Category for water bodies.
        POOP (int): Category for Poop entities.
        SENSOR (int): Category for vision/interaction sensors.
        ALL (int): Mask for colliding with everything.
    """

    GROUND_UNIT = 0b0000_0001
    FLYING_UNIT = 0b0000_0010
    ITEM = 0b0000_0100
    LOW_OBSTACLE = 0b0000_1000
    HIGH_OBSTACLE = 0b0001_0000
    WATER = 0b0010_0000
    POOP = 0b0100_0000
    SENSOR = 0b1000_0000
    ALL = 0xFFFFFFFF

    # Legacy aliases for backwards compatibility
    YUKKURI = GROUND_UNIT
    WALL = HIGH_OBSTACLE
