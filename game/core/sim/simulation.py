"""
The main simulation loop for the game.
"""

import math
from game.core.ai.ai_system import AIController
from game.core.ecs.components import Needs, AIProfile, Blackboard, Position
from game.core.sim.action_resolver import resolve_actions
from game.core.state.game_state import GameState


class Simulation:
    """Orchestrates the game's simulation."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self._ai_controllers: dict[int, AIController] = {}

    def update(self, dt: float):
        """
        Advances the simulation by a time step.

        :param dt: The time delta in seconds.
        """
        for entity in self.game_state.entities:
            # Update needs
            if entity.has_component(Needs):
                needs = entity.get_component(Needs)
                needs.values["hunger"] = min(1.0, needs.values.get("hunger", 0) + 0.01 * dt)
                needs.values["energy"] = max(0.0, needs.values.get("energy", 0) - 0.02 * dt)

            # Run AI
            if entity.has_component(AIProfile):
                if not entity.has_component(Blackboard):
                    entity.add_component(Blackboard())

                if entity.entity_id not in self._ai_controllers:
                    profile = entity.get_component(AIProfile)
                    self._ai_controllers[entity.entity_id] = AIController(profile.behavior["actions"], self.game_state)

                ai_controller = self._ai_controllers[entity.entity_id]
                best_action = ai_controller.decide(entity)

                blackboard = entity.get_component(Blackboard)
                blackboard.data["current_action"] = best_action.schema["id"] if best_action else "idle"

            # Resolve actions
            resolve_actions(entity, self.game_state, dt)

            # --- Movement ---
            if entity.has_component(Blackboard) and entity.has_component(Position):
                blackboard = entity.get_component(Blackboard)
                if "target_position" in blackboard.data:
                    pos = entity.get_component(Position)
                    target_pos = blackboard.data["target_position"]

                    dx = target_pos[0] - pos.x
                    dy = target_pos[1] - pos.y
                    dist = math.sqrt(dx*dx + dy*dy)

                    if dist < 1.0:
                        del blackboard.data["target_position"] # Arrived
                    else:
                        speed = 50.0 # pixels per second
                        pos.x += (dx / dist) * speed * dt
                        pos.y += (dy / dist) * speed * dt
