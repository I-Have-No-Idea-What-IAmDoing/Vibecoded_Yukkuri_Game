"""
Collision Category Constants.
"""


class CollisionCategories:
    """
    Bitmask categories for Pymunk collision filtering.

    Attributes:
        YUKKURI (int): Category for Yukkuri entities.
        ITEM (int): Category for Item entities.
        WALL (int): Category for Wall/Obstacle entities.
        POOP (int): Category for Poop entities.
        ALL (int): Mask for colliding with everything.
    """

    YUKKURI = 0b0001
    ITEM = 0b0010
    WALL = 0b0100
    POOP = 0b1000
    ALL = 0xFFFFFFFF
