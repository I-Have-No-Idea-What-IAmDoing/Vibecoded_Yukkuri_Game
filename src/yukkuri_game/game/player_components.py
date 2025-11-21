from dataclasses import dataclass
from ..engine.ecs import Component

@dataclass
class PlayerState:
    """
    Component representing the global state of the player.
    There should typically be only one entity with this component (Singleton).

    Attributes:
        money (int): The current amount of money the player has.
        time_elapsed (float): Total game time elapsed in seconds.
        save_dir (str): Directory where save files are stored.
    """
    money: int = 1000
    time_elapsed: float = 0.0
    save_dir: str = "saves"
