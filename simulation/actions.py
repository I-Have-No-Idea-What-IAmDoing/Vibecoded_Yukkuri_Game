from __future__ import annotations
import math
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.agent import Agent
    from simulation.world import World

class Action:
    def __init__(self, template: Dict[str, Any]) -> None:
        self.name: str = template['name']
        self.preconditions: List[Dict[str, Any]] = template['preconditions']
        self.effects: List[Dict[str, Any]] = template['effects']
        self.duration: float = template['duration_secs']
        self.score_config: Dict[str, Any] = template['score']
        self.cooldown: float = template['cooldown_secs']
        self.time_started: float = 0.0
        self.on_cooldown: bool = False

    def is_available(self, agent: Agent, world: World) -> bool:
        """Checks if the action can be performed."""
        if self.on_cooldown:
            return False

        for precondition in self.preconditions:
            if not self._check_precondition(agent, world, precondition):
                return False
        return True

    def _check_precondition(self, agent: Agent, world: World, precondition: Dict[str, Any]) -> bool:
        """Checks a single precondition."""
        if precondition['type'] == 'need_below':
            need = agent.needs.get(precondition['need'])
            if need is None or need.value >= precondition['threshold']:
                return False
        elif precondition['type'] == 'near_item_category':
            radius = precondition.get('radius', 1)
            category = precondition['category']

            is_item_nearby = False
            for item in world.placed_items:
                if category in item['def']['categories']:
                    dist = math.hypot(agent.position[0] - item['x'], agent.position[1] - item['y'])
                    if dist <= radius:
                        is_item_nearby = True
                        break
            if not is_item_nearby:
                return False
        return True

    def apply_effects(self, agent: Agent) -> None:
        """Applies the action's effects to the agent."""
        for effect in self.effects:
            if effect['type'] == 'modify_need':
                need = agent.needs.get(effect['need'])
                if need:
                    need.add(effect['delta'])

    def __repr__(self) -> str:
        return f"Action({self.name})"
