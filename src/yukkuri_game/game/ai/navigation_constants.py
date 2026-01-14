from enum import IntFlag, Enum


class TraversalCapability(IntFlag):
    WALK = 0x01  # Ground
    FLY = 0x02  # Air (ignores low obstacles)
    SWIM = 0x04  # Water


class TerrainType(Enum):
    ROAD = 0.5  # Preferred path
    GRASS = 1.0  # Standard
    MUD = 2.0  # Avoid unless necessary
    HAZARD = 10.0  # Soft avoidance
