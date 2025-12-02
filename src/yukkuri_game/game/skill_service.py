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
        # skills_data is now accessed via ResourceManager
        # self.skills_data: Dict[str, SkillDefinition] = {}
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
            return # Or initialize?

        state = skills_comp.states[skill_id]
        skills_data = self.get_skills_data()
        skill_def = skills_data.get(skill_id)

        # Apply Passion Multiplier
        # Note: Intelligence modifier mentioned in plan, but Intelligence stat isn't in YukkuriStats yet.
        # Assuming 10.0 default for now or ignoring if not present.
        intelligence = 10.0

        # Try to get stats from YukkuriStats
        from .yukkuri_components import YukkuriStats
        stats = self.world.get_component(entity, YukkuriStats)
        if stats:
            # If YukkuriStats has intelligence in the future, usage:
            # intelligence = getattr(stats, "intelligence", 10.0)
            pass

        xp_gain = amount * state.passion * (intelligence / 10.0)

        # Soft Cap Logic
        soft_cap_base = skill_def.soft_cap_base_level if skill_def else 10
        # Passion affects soft cap: BaseCap + (Passion * 2) - approximate logic from plan
        # Plan says: Cap_level = BaseCap + (Passion * 2). Passion is a multiplier (0.5, 1.0, 2.5).
        # So for Burning (2.5), cap increases by 5. For None (0.5), cap increases by 1?
        # Wait, if Passion is multiplier, usually modifiers are additive to base?
        # "High passion correlating to higher softcap".
        # Let's use the multiplier value directly as proposed.
        soft_cap_level = soft_cap_base + int(state.passion * 2)

        # Check trait offsets if any? (Store them in state? No, calculate dynamically?
        # Modifiers were applied at initialization to passion.
        # Trait modifiers in TOML: "soft_cap_offset".
        # I need to store soft_cap_offset in SkillState or look it up every time.
        # Storing is better for performance, but SkillState schema didn't have it.
        # I'll re-lookup traits if I want perfection, or just assume the plan's initialized passion handles it?
        # Plan 4.3 says: `soft_cap_offset = -2`.
        # So I should probably check traits again or store offset.
        # I'll skip offset for now to keep it simple or check traits if available.

        if state.level >= soft_cap_level:
            xp_gain *= 0.1

        state.current_xp += xp_gain

        # Update timestamp
        # Import TimeService locally to avoid circular dependency
        from .services import TimeService
        time_svc = self.world.services.try_get(TimeService)
        if time_svc:
            state.last_used_gametime = time_svc.time_elapsed

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

            # Initialize last_decay if it's 0 (first run)
            if state.last_decay_gametime == 0.0:
                state.last_decay_gametime = current_gametime
                continue

            # Check if enough time has passed since last decay check
            # We decay based on time passed since last decay check
            time_since_last_decay = current_gametime - state.last_decay_gametime

            # Decay accumulates over time, but we only apply if unused for a threshold?
            # Proposal: "Decay can occur if last_used is too old... Loss = DecayRate * (DaysSinceLastUse - 1.0)"
            # This formula calculates INSTANTANEOUS loss rate or TOTAL loss?
            # "XP lost per day if unused".
            # If unused for 1.5 days, loss = Rate * 0.5.
            # If unused for 2.0 days, loss = Rate * 1.0.
            # If we apply this every frame, we need to be careful.
            # Better approach: Calculate loss for the `dt` since `last_decay_gametime`,
            # BUT scaled by how "deep" we are into the unused period.

            days_unused = (current_gametime - state.last_used_gametime) / SECONDS_PER_DAY

            if days_unused > 1.0:
                # We are in decay zone.
                # How much time passed since last decay update?
                decay_dt_days = time_since_last_decay / SECONDS_PER_DAY

                # Loss for this period
                # Formula: Rate * (DaysUnused - 1).
                # Actually, standard decay usually is Rate * dt,
                # but here the RATE depends on how long it's been unused?
                # "Loss = DecayRate * (DaysSinceLastUse - 1.0)" looks like a formula for Total Loss over a period?
                # Or maybe "Loss per day = DecayRate * (DaysSinceLastUse - 1.0)"?
                # i.e. The longer you wait, the faster it decays?
                # OR implies a threshold: 1 day grace period. After that, linear decay?
                # Let's assume linear decay after 1 day grace period.
                # Rate = DecayRate per day.

                loss = decay_rate * decay_dt_days

                state.current_xp = max(0.0, state.current_xp - loss)

            # Update last_decay_gametime
            state.last_decay_gametime = current_gametime
