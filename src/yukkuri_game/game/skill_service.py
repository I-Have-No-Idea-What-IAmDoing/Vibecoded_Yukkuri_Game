"""
Service for managing Yukkuri skills, XP gain, leveling, and decay.
"""
import math
import os
import sys

from typing import Dict, Any, Optional, TYPE_CHECKING
from loguru import logger
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager
from .yukkuri_components import Skills, SkillState, Personality
from .skill_constants import SkillId, PassionLevel
from .trait_service import TraitService

if TYPE_CHECKING:
    from .services import TimeService
    from ..engine.data_models import SkillDefinition

class SkillService:
    """
    Service responsible for handling skill mechanics.
    """

    def __init__(self, world: World):
        self.world = world
        pass

    def get_skills_data(self) -> Dict[str, "SkillDefinition"]:
        """Retrieves loaded skills data from ResourceManager."""
        rm = self.world.services.try_get(ResourceManager)
        if rm:
            return rm.skills
        return {}

    def initialize_skills(self, entity: int) -> None:
        """
        Initializes skills for a Yukkuri based on its personality traits.

        Args:
            entity (int): The entity ID.
        """
        if not self.world.entity_exists(entity):
            return

        # Ensure entity has Skills component
        if not self.world.has_component(entity, Skills):
            self.world.add_component(entity, Skills())

        skills_comp = self.world.get_component(entity, Skills)
        personality = self.world.get_component(entity, Personality)
        trait_service = self.world.services.try_get(TraitService)

        trait_modifiers = {}
        if personality and trait_service:
            for trait_id in personality.traits:
                trait_data = trait_service.get_trait(trait_id)
                if trait_data and "skill_modifiers" in trait_data:
                    for skill_key, mods in trait_data["skill_modifiers"].items():
                        if skill_key not in trait_modifiers:
                            trait_modifiers[skill_key] = mods
                        else:
                            # Simple merge: last one wins for conflicting keys
                            trait_modifiers[skill_key].update(mods)

        skills_data = self.get_skills_data()
        for skill_id, skill_def in skills_data.items():
            state = SkillState()

            # Apply base passion or derived passion
            passion_mult = PassionLevel.NORMAL.value

            # Check modifiers
            if skill_id in trait_modifiers:
                mods = trait_modifiers[skill_id]
                if "passion_multiplier" in mods:
                    passion_mult = mods["passion_multiplier"]

            state.passion = passion_mult

            # Initialize timestamps
            from .services import TimeService
            time_svc = self.world.services.try_get(TimeService)
            if time_svc:
                state.last_used_gametime = time_svc.time_elapsed
                state.last_decay_gametime = time_svc.time_elapsed

            skills_comp.states[skill_id] = state

    def get_xp_required(self, level: int) -> float:
        """
        Calculates XP required to go from current level to next level.
        Formula: 100 * (1.5 ^ Level)
        """
        return 100.0 * (1.5 ** level)

    def add_xp(self, entity: int, skill_id: str, amount: float) -> None:
        """
        Adds XP to a skill. Handles leveling up and soft caps.

        Args:
            entity (int): The entity ID.
            skill_id (str): The ID of the skill.
            amount (float): Base XP amount to add.
        """
        if not self.world.has_component(entity, Skills):
            return

        skills_comp = self.world.get_component(entity, Skills)
        if skill_id not in skills_comp.states:
            return

        state = skills_comp.states[skill_id]
        skills_data = self.get_skills_data()
        skill_def = skills_data.get(skill_id)

        # Intelligence modifier (placeholder)
        intelligence = 10.0
        from .yukkuri_components import YukkuriStats
        stats = self.world.get_component(entity, YukkuriStats)
        if stats:
            # intelligence = getattr(stats, "intelligence", 10.0)
            pass

        xp_gain = amount * state.passion * (intelligence / 10.0)

        # Soft Cap Logic
        soft_cap_base = skill_def.soft_cap_base_level if skill_def else 10
        # Passion affects soft cap: BaseCap + (Passion * 2)
        soft_cap_level = soft_cap_base + int(state.passion * 2)

        if state.level >= soft_cap_level:
            xp_gain *= 0.1

        state.current_xp += xp_gain

        # Update timestamp
        from .services import TimeService
        time_svc = self.world.services.try_get(TimeService)
        if time_svc:
            state.last_used_gametime = time_svc.time_elapsed
            # Reset decay timer so we don't decay immediately after use
            state.last_decay_gametime = time_svc.time_elapsed

        # Check Level Up
        required = self.get_xp_required(state.level)
        while state.current_xp >= required:
            max_lvl = skill_def.max_level if skill_def else 20
            if state.level < max_lvl:
                state.current_xp -= required
                state.level += 1
                logger.info(f"Entity {entity} leveled up {skill_id} to {state.level}!")
                # TODO: Notify UI/EventBus
                required = self.get_xp_required(state.level)
            else:
                state.current_xp = required # Cap at max
                break

    def evaluate_condition(self, entity: int, condition_str: str) -> bool:
        """
        Evaluates a condition string against an entity's skills.
        Format: "skill:<skill_id> > <level>"

        Args:
            entity (int): The entity ID.
            condition_str (str): The condition string.

        Returns:
            bool: True if condition is met, False otherwise.
        """
        if not condition_str.startswith("skill:"):
            return False

        parts = condition_str.split(" ")
        if len(parts) != 3:
            return False

        key_part = parts[0] # skill:name
        op = parts[1] # >
        val = parts[2] # level

        skill_id = key_part.split(":")[1]

        if not self.world.has_component(entity, Skills):
            return False

        skills = self.world.get_component(entity, Skills)
        state = skills.states.get(skill_id)

        if not state:
            return False

        try:
            threshold = float(val)
        except ValueError:
            return False

        if op == ">":
            return state.level > threshold
        elif op == ">=":
            return state.level >= threshold
        elif op == "<":
            return state.level < threshold
        elif op == "<=":
            return state.level <= threshold
        elif op == "==":
            return state.level == threshold

        return False

    def apply_decay(self, entity: int, current_gametime: float) -> None:
        """
        Applies decay to skills based on time since last use.
        Decay only starts after a 1-day grace period of disuse.

        Args:
            entity (int): The entity ID.
            current_gametime (float): Current game time in seconds.
        """
        if not self.world.has_component(entity, Skills):
            return

        skills_comp = self.world.get_component(entity, Skills)
        SECONDS_PER_DAY = 600.0 # Example value

        skills_data = self.get_skills_data()
        for skill_id, state in skills_comp.states.items():
            skill_def = skills_data.get(skill_id)
            if not skill_def:
                continue

            decay_rate = skill_def.decay_rate
            if decay_rate <= 0:
                continue

            if state.last_decay_gametime == 0.0:
                state.last_decay_gametime = current_gametime
                continue

            # Decay logic:
            # We want to decay only for the duration that is BEYOND (last_used + 1 day).

            threshold_time = state.last_used_gametime + SECONDS_PER_DAY

            # The start of the decay calculation interval is either the last time we checked,
            # or the threshold time, whichever is later.
            start_calc_time = max(state.last_decay_gametime, threshold_time)
            end_calc_time = current_gametime

            if end_calc_time > start_calc_time:
                # Calculate duration in days
                dt_days = (end_calc_time - start_calc_time) / SECONDS_PER_DAY

                loss = decay_rate * dt_days

                # Ensure we don't drop below 0 for current level progress
                state.current_xp = max(0.0, state.current_xp - loss)

            # Update last_decay_gametime to now
            state.last_decay_gametime = current_gametime
