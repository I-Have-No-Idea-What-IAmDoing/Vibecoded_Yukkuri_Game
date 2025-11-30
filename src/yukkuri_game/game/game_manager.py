"""
Module defining the GameManager logic.
"""
from typing import TYPE_CHECKING
from ..engine.ecs import World

if TYPE_CHECKING:
    from .entity_factory import EntityFactory

class GameManager:
    """
    Deprecated. Logic moved to GameRulesSystem and GameplayScene.
    Kept as empty class for strict typing if necessary, but ideally should be removed.
    """
    def __init__(self, world: World):
        pass
