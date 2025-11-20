from dataclasses import dataclass
from typing import Dict, Any
from ..engine.ecs import Component

# Yukkuri Specific Components

@dataclass
class YukkuriStats:
    name: str
    type_id: str
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0      # 0 = full, 100 = starving
    happiness: float = 50.0  # 0 = sad, 100 = happy
    cleanliness: float = 100.0
    age: float = 0.0         # In game seconds/ticks
    growth_stage: str = "Baby" # Baby, Child, Adult
    badges: int = 0
    quality_score: float = 0.0

@dataclass
class AIState:
    current_action: str = "Idle"
    current_target_id: int = -1
    path: list = None
    action_progress: float = 0.0
    state_data: Dict[str, Any] = None

@dataclass
class ItemStats:
    name: str
    type_id: str
    cost: int
    nutrition: float = 0.0
    fun: float = 0.0
    comfort: float = 0.0
    is_portable: bool = False
