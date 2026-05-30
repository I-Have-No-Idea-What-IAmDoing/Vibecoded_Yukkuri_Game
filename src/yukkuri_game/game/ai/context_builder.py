"""
Module for building context dictionaries used by the Utility AI system.
Extracts the complex logic of converting World/Component state into a flat dictionary
from the UtilitySelector, promoting separation of concerns.
"""

from typing import Any, TYPE_CHECKING

from ...engine.services.time_service import TimeService
from ..trait_service import TraitService
from ..components import (
    Blackboard,
    EmotionalState,
    Needs,
    Personality,
    Predator,
    Skills,
    YukkuriStats,
)
from ...engine.components import Transform


if TYPE_CHECKING:
    from ...engine.ecs import World


class UtilityContextBuilder:
    """
    Builder class responsbile for constructing the context dictionary for Utility AI evaluation.
    """

    @staticmethod
    def build_context(
        entity_id: int,
        world: "World",
        trait_service: "TraitService | None" = None,
    ) -> dict[str, Any] | None:
        """
        Builds the context dictionary for the given entity.

        Args:
            entity_id (int): The ID of the entity.
            world (World): The ECS World instance.
            trait_service (TraitService | None): Optional service for looking up trait data.

        Returns:
            dict[str, Any] | None: The context dictionary, or None if critical components are missing.
        """
        stats = world.try_get_component(entity_id, YukkuriStats)
        needs = world.try_get_component(entity_id, Needs)
        trans = world.try_get_component(entity_id, Transform)

        if not stats or not needs:
            return None

        personality = world.try_get_component(entity_id, Personality)
        emotional = world.try_get_component(entity_id, EmotionalState)
        skills = world.try_get_component(entity_id, Skills)
        blackboard = world.try_get_component(entity_id, Blackboard)
        time_service = world.services.try_get(TimeService)

        # 1. Blackboard Data
        nearby_friends = 0.0
        nearby_enemies = 0.0
        nearby_prey = 0.0

        if blackboard:
            nearby_friends = float(blackboard.nearby_friends)
            nearby_enemies = float(blackboard.nearby_enemies)
            nearby_prey = float(blackboard.nearby_prey)

        # 2. Emotional State
        happiness = 50.0
        stress = 0.0
        if emotional:
            # Normalize -100..100 to 0..100
            happiness = (emotional.happiness + 100.0) / 2.0
            stress = emotional.stress

        # 3. Environment (Time)
        time_of_day = 12.0
        is_night = 0.0
        if time_service:
            time_of_day = time_service.time_of_day
            if time_service.is_night:
                is_night = 1.0

        # 3b. Environment (Lights)
        nearby_lights = 0.0
        from ...engine.components import LightSource
        from ...engine.protocols import ISpatialService
        spatial_service = world.services.try_get(ISpatialService)
        if spatial_service and trans:
            best_light = spatial_service.get_nearest_entity(
                world,
                trans.x,
                trans.y,
                component_filter=LightSource,
                max_radius=2000.0,
                exclude_ids={entity_id},
            )
            if best_light != -1:
                light_comp = world.try_get_component(best_light, LightSource)
                if light_comp and light_comp.intensity > 0.0:
                    nearby_lights = 1.0
        else:
            for l_ent, l_comp in world.get_components(LightSource).items():
                if l_comp.intensity > 0.0:
                    nearby_lights = 1.0
                    break

        # 3c. Environment (Items availability)
        has_food = 1.0
        has_toy = 1.0
        has_bed = 1.0
        from ..services import GameService
        game_service = world.services.try_get(GameService)
        if game_service and trans:
            pos = (trans.x, trans.y)
            food_item = game_service.find_best_item(pos, "nutrition", searcher_id=entity_id)
            has_food = 1.0 if food_item != -1 else 0.0

            toy_item = game_service.find_best_item(pos, "fun", searcher_id=entity_id)
            has_toy = 1.0 if toy_item != -1 else 0.0

            bed_item = game_service.find_best_item(pos, "comfort", searcher_id=entity_id)
            has_bed = 1.0 if bed_item != -1 else 0.0

        # 4. Construct Core Context
        context = {
            "hunger": needs.hunger,
            "hunger_inv": 100.0 - needs.hunger,
            "energy": needs.energy,
            "energy_inv": 100.0 - needs.energy,
            "happiness": happiness,
            "happiness_inv": 100.0 - happiness,
            "social": needs.social,
            "social_inv": 100.0 - needs.social,
            "stress": stress,
            "cleanliness": needs.cleanliness,
            "bladder": needs.bladder,
            "easiness": needs.easiness,
            "nearby_friends": nearby_friends,
            "nearby_enemies": nearby_enemies,
            "nearby_prey": nearby_prey,
            "time_of_day": time_of_day,
            "is_night": is_night,
            "nearby_lights": nearby_lights,
            "has_food": has_food,
            "has_toy": has_toy,
            "has_bed": has_bed,
            "constant_100": 100.0,
            "constant_0": 0.0,
            "is_predator": 1.0 if world.has_component(entity_id, Predator) else 0.0,
        }

        # 5. Inject Skills
        if skills:
            for skill_id, state in skills.states.items():
                context[f"skill_{skill_id}"] = float(state.level)

        # 6. Inject Personality & Traits
        if personality:
            if personality.axis:
                context["val_kindness"] = (personality.axis.kindness + 100) / 2.0
                context["val_energy"] = (personality.axis.energy + 100) / 2.0
                context["val_bravery"] = (personality.axis.bravery + 100) / 2.0
                context["val_greed"] = (personality.axis.greed + 100) / 2.0
                context["val_compassion"] = context["val_kindness"]  # Alias

            # Traits as binary flags
            for trait in personality.traits:
                context[f"trait_{trait}"] = 1.0

            # Ensure overrides are cached
            if trait_service and personality.cached_overrides is None:
                personality.cached_overrides = trait_service.calculate_overrides(
                    personality.traits
                )

        return context
