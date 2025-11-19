from __future__ import annotations
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from simulation.actions import Action

if TYPE_CHECKING:
    from simulation.agent import Agent
    from simulation.world import World

class UtilityAI:
    def __init__(self, action_templates: List[Dict[str, Any]]) -> None:
        self.actions: List[Action] = [Action(template) for template in action_templates]

    def select_action(self, agent: Agent, world: World) -> Optional[Action]:
        """Selects the best action for an agent based on utility scores."""
        best_action: Optional[Action] = None
        highest_score: float = -1.0

        for action in self.actions:
            if action.is_available(agent, world):
                score = self._score_action(agent, action)
                if score > highest_score:
                    highest_score = score
                    best_action = action

        return best_action

    def _score_action(self, agent: Agent, action: Action) -> float:
        """Calculates the score for a single action."""
        score_config = action.score_config
        if score_config['type'] == 'weighted_sum':
            return self._score_weighted_sum(agent, score_config)
        return 0.0

    def _score_weighted_sum(self, agent: Agent, config: Dict[str, Any]) -> float:
        """Calculates score based on a weighted sum of signals."""
        total_score: float = config.get('bias', 0.0)
        for term in config['terms']:
            signal_value = self._get_signal_value(agent, term)
            total_score += signal_value * term['weight']
        return total_score

    def _get_signal_value(self, agent: Agent, term: Dict[str, Any]) -> float:
        """Gets the value of a specific signal."""
        if term['signal'] == 'need_inverse':
            need = agent.needs.get(term['need'])
            if need:
                return (need.max - need.value) / (need.max - need.min) if need.max > need.min else 0.0
        return 0.0
