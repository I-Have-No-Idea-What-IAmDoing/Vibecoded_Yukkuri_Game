"""
Prefab for the Player entity.
"""
from ...engine.ecs import World
from ..components import Transform
from ..components_persistence import StableIDComponent, Persistable

def create_player(world: World, x: float = 0, y: float = 0) -> int:
    """
    Creates a Player entity (representing the god hand/camera/global state).
    """
    entity = world.create_entity()
    world.add_component(entity, Transform(x=x, y=y))
    world.add_component(entity, StableIDComponent(id="player")) # Fixed ID for player
    world.add_component(entity, Persistable())
    return entity
