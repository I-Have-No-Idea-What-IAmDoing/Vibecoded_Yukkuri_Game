from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from simulation.needs import Need
from simulation.utility_ai import UtilityAI
from simulation.pathfinding import astar_pathfind
import math
import random

if TYPE_CHECKING:
    from simulation.world import World
    from game.app import App
    from simulation.actions import Action


class Agent:
    def __init__(self, archetype: Dict[str, Any], position: Tuple[int, int], action_templates: List[Dict[str, Any]]) -> None:
        self.archetype_id: str = archetype['id']
        self.display_name: str = archetype['display_name']
        self.stats: Dict[str, Any] = archetype['stats']
        self.position: List[float] = [position[0], position[1]]

        self.needs: Dict[str, Need] = {}
        for need_data in archetype['needs']:
            self.needs[need_data['name']] = Need(
                name=need_data['name'],
                min_val=need_data['min'],
                max_val=need_data['max'],
                initial_val=need_data['initial'],
                decay_per_min=need_data['decay_per_min']
            )

        self.utility_ai: UtilityAI = UtilityAI(action_templates)
        self.current_action: Optional[Action] = None
        self.action_timer: float = 0.0
        self.path: Optional[List[Tuple[int, int]]] = None
        self.target_item: Optional[Dict[str, Any]] = None
        self.state: str = 'IDLE' # IDLE, NAVIGATING, INTERACTING
        self.dialogue_timer: float = 5.0

    def update(self, delta_time: float, world: World, app: App) -> None:
        for need in self.needs.values():
            need.update(delta_time)

        if self.state == 'IDLE':
            self._decide_next_action(world)
            self._update_dialogue(delta_time, app)
        elif self.state == 'NAVIGATING':
            self._follow_path(delta_time)
        elif self.state == 'INTERACTING':
            self._perform_interaction(delta_time)

    def _decide_next_action(self, world: World) -> None:
        chosen_action = self.utility_ai.select_action(self, world)
        if chosen_action:
            self.current_action = chosen_action
            if any(p['type'] == 'near_item_category' for p in self.current_action.preconditions):
                self._find_and_navigate_to_item(world)
            else:
                self.state = 'INTERACTING'
                self.action_timer = self.current_action.duration

    def _find_and_navigate_to_item(self, world: World) -> None:
        category = next(p['category'] for p in self.current_action.preconditions if p['type'] == 'near_item_category')

        target_item = self._find_closest_item_of_category(world, category)
        if target_item:
            self.target_item = target_item
            interact_pos_def = target_item['def']['interact_slot']
            target_pos = (target_item['x'] + interact_pos_def['x'], target_item['y'] + interact_pos_def['y'])

            if not (0 <= target_pos[0] < world.width and 0 <= target_pos[1] < world.height):
                self.current_action = None
                return

            self.path = astar_pathfind(world.grid, tuple(map(int, self.position)), target_pos)
            if self.path:
                self.state = 'NAVIGATING'
            else:
                self.current_action = None
        else:
            self.current_action = None

    def _find_closest_item_of_category(self, world: World, category: str) -> Optional[Dict[str, Any]]:
        closest_item: Optional[Dict[str, Any]] = None
        min_dist = float('inf')
        for item in world.placed_items:
            if category in item['def']['categories']:
                dist = math.hypot(self.position[0] - item['x'], self.position[1] - item['y'])
                if dist < min_dist:
                    min_dist = dist
                    closest_item = item
        return closest_item

    def _follow_path(self, delta_time: float) -> None:
        if not self.path:
            self.state = 'IDLE'
            return

        target_pos = self.path[0]
        direction = [target_pos[0] - self.position[0], target_pos[1] - self.position[1]]
        dist = math.hypot(direction[0], direction[1])

        if dist > 0:
            direction = [direction[0] / dist, direction[1] / dist]
            speed = self.stats['speed']
            self.position[0] += direction[0] * speed * delta_time
            self.position[1] += direction[1] * speed * delta_time

        if math.hypot(target_pos[0] - self.position[0], target_pos[1] - self.position[1]) < 0.1:
            self.position = list(target_pos)
            self.path.pop(0)
            if not self.path:
                self.state = 'INTERACTING'
                if self.current_action:
                    self.action_timer = self.current_action.duration

    def _perform_interaction(self, delta_time: float) -> None:
        self.action_timer -= delta_time
        if self.action_timer <= 0:
            if self.current_action:
                self.current_action.apply_effects(self)
            self.current_action = None
            self.state = 'IDLE'

    def _update_dialogue(self, delta_time: float, app: App) -> None:
        self.dialogue_timer -= delta_time
        if self.dialogue_timer <= 0:
            line = app.dialogue_manager.get_line("idle")
            if line:
                app.event_bus.publish("agent_spoke", {'agent': self, 'text': line})

            self.dialogue_timer = random.uniform(5.0, 15.0)

    def __repr__(self) -> str:
        return f"Agent({self.display_name}, state={self.state}, action={self.current_action.name if self.current_action else 'None'})"
