"""
Module for managing Yukkuri skills, XP gain, and leveling.
"""
import os
import sys
import math
from typing import Dict, Any, Optional
from loguru import logger

# For now we use the built-in tomllib for loading.
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import tomllib

from ..engine.ecs import World
from .yukkuri_components import Skills, SkillData, Personality, YukkuriStats
from .trait_service import TraitService
from .services import TimeService

class SkillService:
    """
    Service responsible for loading skill definitions, initializing skills,
    and managing XP gain and leveling.
    """

    def __init__(self, world: World):
        self.world = world
        self.skill_definitions: Dict[str, Any] = {}
        self.data_dir = os.path.join("data")
        self.load_data()

    def load_data(self) -> None:
        """Loads skill definitions from TOML."""
        skills_path = os.path.join(self.data_dir, "skills", "skills.toml")
        if not os.path.exists(skills_path):
            logger.warning(f"File not found: {skills_path}")
            return

        try:
            with open(skills_path, "rb") as f:
                data = tomllib.load(f)
                self.skill_definitions = data.get("skills", {})
            logger.info(f"Loaded {len(self.skill_definitions)} skill definitions.")
        except Exception as e:
            logger.error(f"Failed to load {skills_path}: {e}")

    def initialize_skills(self, entity_id: int) -> None:
        """
        Initializes the Skills component for a Yukkuri, setting base passions based on traits.
        """
        if not self.world.has_component(entity_id, Skills):
            self.world.add_component(entity_id, Skills())

        skills_comp = self.world.get_component(entity_id, Skills)
        personality = self.world.get_component(entity_id, Personality)
        trait_service = self.world.services.try_get(TraitService)

        # Initialize all defined skills
        for skill_id in self.skill_definitions.keys():
            if skill_id not in skills_comp.skills:
                skills_comp.skills[skill_id] = SkillData()

        # Apply Passion modifiers from Traits
        if personality and trait_service:
            for trait_id in personality.traits:
                trait_data = trait_service.get_trait(trait_id)
                if trait_data and "skill_modifiers" in trait_data:
                    mods = trait_data["skill_modifiers"]
                    for skill_id, mod_data in mods.items():
                        if skill_id in skills_comp.skills:
                            # Assuming mod_data can directly set passion or contain passion multiplier
                            # For simplicity, let's assume the trait defines the passion level directly or a multiplier
                            # Example trait data: { "skill_modifiers": { "athletics": { "passion": 2.5 } } }
                            if "passion" in mod_data:
                                skills_comp.skills[skill_id].passion = float(mod_data["passion"])

    def gain_xp(self, entity_id: int, skill_id: str, amount: float) -> None:
        """
        Grants XP to a specific skill for an entity.
        """
        skills_comp = self.world.get_component(entity_id, Skills)
        if not skills_comp or skill_id not in skills_comp.skills:
            return

        skill_data = skills_comp.skills[skill_id]
        defn = self.skill_definitions.get(skill_id)
        if not defn:
            return

        # Apply Passion Multiplier
        final_xp = amount * skill_data.passion

        # Apply Intelligence Modifier (if we had an intelligence stat, for now just use 1.0)
        # Maybe use Growth Stage? Adults learn faster? Babies slower? Or vice versa?
        # Let's keep it simple for now.

        # Softcap Logic
        # Calculate softcap based on passion (higher passion = higher softcap)
        # Base softcap = 10. Passion 2.5x -> Softcap 25?
        # Let's say softcap is Level 10 for normal (1.0), Level 5 for 0.5, Level 15 for 1.5, Level 20 for 2.5
        softcap_level = 10.0 * skill_data.passion

        if skill_data.level >= softcap_level:
            final_xp *= 0.1 # Reduced gain past softcap

        skill_data.xp += final_xp

        # Update last used time
        time_service = self.world.services.try_get(TimeService)
        if time_service:
            skill_data.last_used = time_service.time_elapsed

        # Check for Level Up
        self._check_level_up(entity_id, skill_id, skill_data, defn)

    def _check_level_up(self, entity_id: int, skill_id: str, skill_data: SkillData, defn: Dict[str, Any]) -> None:
        """
        Checks if the skill should level up based on current XP.
        """
        max_level = defn.get("max_level", 20)
        if skill_data.level >= max_level:
            return

        # XP Curve: Level^2 * 100 (Example)
        # Level 0 -> 1: 0 XP
        # Level 1 -> 2: 100 XP
        # Level 2 -> 3: 400 XP
        next_level_xp = ((skill_data.level + 1) ** 2) * 100

        if skill_data.xp >= next_level_xp:
            skill_data.level += 1
            skill_data.xp -= next_level_xp # Or keep cumulative?
            # Proposal says "When XP reaches a threshold, Level increases."
            # Usually accumulating XP is easier for "total xp" tracking, but resetting is easier for "next level" bar.
            # Let's assume cumulative XP is NOT stored, but we subtract cost.
            # WAIT: "Experience (XP): A floating-point value. Actions grant XP. When XP reaches a threshold, the Level increases."
            # Let's stick to: XP is progress to NEXT level.

            # Notify / Floating Text
            from .prefabs.effects import create_floating_text
            from .components import Transform
            trans = self.world.get_component(entity_id, Transform)
            if trans:
                 create_floating_text(self.world, trans.x, trans.y - 40, f"{defn['name']} Up! ({skill_data.level})", (100, 255, 255))

            logger.info(f"Entity {entity_id} leveled up {skill_id} to {skill_data.level}")

            # Recurse in case of massive XP gain
            self._check_level_up(entity_id, skill_id, skill_data, defn)

    def get_skill_level(self, entity_id: int, skill_id: str) -> int:
        """Returns the level of a skill, or 0 if not present."""
        skills_comp = self.world.get_component(entity_id, Skills)
        if skills_comp and skill_id in skills_comp.skills:
            return skills_comp.skills[skill_id].level
        return 0

    def update_skills(self, current_time: float) -> None:
        """
        Updates skills for decay.
        Usually called by a system every frame, but we should gate it to run less often.
        """
        # Optimization: Only run once every ~10 game minutes (600 seconds)
        # We need to store last update time in service.
        if not hasattr(self, "_last_update_check"):
            self._last_update_check = 0.0

        if current_time - self._last_update_check < 600.0:
            return

        self._last_update_check = current_time

        # Day length is typically defined in TimeService or just arbitrary.
        # Let's assume 1 day = 24 * 60 * 60 = 86400 seconds (real time seconds representing game time)
        # OR if game time is scaled. Let's assume TimeService returns accumulated seconds.
        DAY_SECONDS = 86400.0
        DECAY_THRESHOLD = DAY_SECONDS # Unused for 1 day

        # Iterate all entities with Skills
        # This is expensive if many entities, but we do it rarely.
        entities_with_skills = self.world.get_components(Skills)

        # World.get_components returns {entity_id: component} dict in wrapper,
        # but esper.get_component returns iterator (entity, component).
        # Wrapper World.get_components(T) -> Dict[int, T]

        for entity_id, skills_comp in entities_with_skills.items():
            for skill_id, skill_data in skills_comp.skills.items():
                if skill_data.level <= 0 and skill_data.xp <= 0:
                    continue

                time_since_last_use = current_time - skill_data.last_used

                if time_since_last_use > DECAY_THRESHOLD:
                    defn = self.skill_definitions.get(skill_id)
                    if defn and "decay_rate" in defn:
                        decay_rate = defn["decay_rate"] # XP lost per day

                        # Calculate days past threshold
                        days_over = (time_since_last_use - DECAY_THRESHOLD) / DAY_SECONDS

                        # We apply decay for the *interval* since last check?
                        # Or just apply based on total time unused?
                        # Simplest is: if unused for > 1 day, apply daily decay rate * delta_time_in_days
                        # But we only check every 10 mins.

                        # Let's subtract decay proportional to time passed since last update check?
                        # No, "decay_rate = 0.1 XP lost per day if unused".
                        # This implies continuous decay as long as unused.

                        # Apply decay for this 600s interval (or whatever time passed since last check)
                        # XP to remove = Rate * (TimeStep / DaySeconds)
                        time_delta = current_time - self._last_update_check
                        if time_delta <= 0: time_delta = 600.0 # Fallback
                        xp_loss = decay_rate * (time_delta / DAY_SECONDS)

                        # Prevent level down? Proposal says: "Decay only affects XP and not levels"
                        if skill_data.xp > 0:
                            skill_data.xp = max(0.0, skill_data.xp - xp_loss)
                            # logger.debug(f"Decayed {skill_id} for entity {entity_id}: -{xp_loss}")
