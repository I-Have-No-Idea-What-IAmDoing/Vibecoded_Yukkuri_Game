from src.engine.ecs import Component
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Transform(Component):
    x: float = 0.0
    y: float = 0.0
    width: float = 32.0
    height: float = 32.0
    vx: float = 0.0
    vy: float = 0.0

@dataclass
class Stats(Component):
    health: float = 100.0
    max_health: float = 100.0
    hunger: float = 0.0 # 0 is full, 100 is starving
    max_hunger: float = 100.0
    happiness: float = 100.0
    max_happiness: float = 100.0
    energy: float = 100.0
    max_energy: float = 100.0
    cleanliness: float = 100.0
    max_cleanliness: float = 100.0
    age: float = 0.0
    growth_stage: str = "Baby" # Baby, Child, Adult
    quality_score: float = 0.0
    badges: int = 0

@dataclass
class Identity(Component):
    name: str = "Yukkuri"
    type_id: str = "unknown"
    description: str = ""
    color: tuple = (255, 255, 255)

@dataclass
class AIComponent(Component):
    current_action: Optional[str] = None
    action_timer: float = 0.0
    action_cooldowns: dict = field(default_factory=dict)
    target_entity_id: Optional[str] = None

@dataclass
class ItemComponent(Component):
    item_type: str = "unknown"
    value: int = 0
    cost: int = 0
    effects: dict = field(default_factory=dict)
