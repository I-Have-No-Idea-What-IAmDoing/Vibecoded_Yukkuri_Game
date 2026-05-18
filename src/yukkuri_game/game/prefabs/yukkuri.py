"""
Prefab functions for Yukkuri entities.
"""

from typing import Any

import pymunk

from yukkuri_game.engine import rng

from ...engine.ecs import World
from ...engine.resource_manager import ResourceManager
from ..collision_constants import CollisionCategories
from ..components import (
    AIState,
    EmotionalState,
    GossipQueue,
    InventoryComponent,
    Needs,
    Personality,
    PersonalityAxis,
    Predator,
    RelationshipRegistry,
    SteeringComponent,
    Vision,
    YukkuriStats,
)
from yukkuri_game.engine.components import (
    Flight,
    FlightState,
    Mount,
    MovementController,
    Persistable,
    Selectable,
    Sprite,
    StableIDComponent,
    Transform,
    VisualTransform,
)
from ..physics_utils import add_physics_body, get_yukkuri_radius
from ..skill_service import SkillService
from yukkuri_game.engine.systems.physics import PhysicsSystem
from ..trait_service import TraitService
from ..utils.animation_helpers import build_animator_from_data


def create_yukkuri(
    world: World,
    type_id: str,
    x: float,
    y: float,
    age: float = 0.0,
    parents: list[int] | None = None,
) -> int:
    """
    Creates a Yukkuri entity.

    Args:
        world (World): The ECS World.
        type_id (str): The Yukkuri type identifier.
        x (float): World x-coordinate.
        y (float): World y-coordinate.
        age (float): Initial age in seconds.
        parents (Optional[List[int]]): IDs of parent entities for genetic inheritance.

    Returns:
        int: The created entity ID.

    Raises:
        ValueError: If the Yukkuri type is unknown.
    """
    rm = world.services.get(ResourceManager)
    world.services.try_get(PhysicsSystem)
    trait_service = world.services.try_get(TraitService)
    skill_service = world.services.try_get(SkillService)

    data = rm.yukkuri_types.get(type_id)
    if not data:
        raise ValueError(f"Unknown yukkuri type: {type_id}")

    entity = world.create_entity()

    try:

        def _get_attr(d: Any, k: str, default: Any = None) -> Any:
            """
            Helper to safely retrieve attributes from either a dict or an object.

            Args:
                d (Any): The source object (dict or class instance).
                k (str): The key or attribute name.
                default (Any): The default value to return if not found.

            Returns:
                Any: The retrieved value or default.
            """
            if isinstance(d, dict):
                return d.get(k, default)
            return getattr(d, k, default)

        image = _get_attr(data, "image", "yukkuri_default.png")
        width = _get_attr(data, "width", 64)
        height = _get_attr(data, "height", 64)
        max_health = _get_attr(data, "max_health", 100)

        # Determine growth stage and scale based on age using shared constants
        from ..yukkuri_constants import STAGE_BABY, get_growth_stage_and_scale

        growth_stage, scale = get_growth_stage_and_scale(age)

        if growth_stage == STAGE_BABY:
            max_health *= 0.5

        radius = get_yukkuri_radius(growth_stage)

        frame_count = _get_attr(data, "frame_count", 1)
        frame_duration = _get_attr(data, "frame_duration", 0.1)
        loop = _get_attr(data, "loop", True)

        world.add_component(entity, Transform(x=x, y=y, scale=scale))

        sprite = Sprite(
            image_name=image,
            width=width,
            height=height,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            is_animating=(frame_count > 1),
        )
        world.add_component(entity, sprite)

        # Animator Creation (Enables Events and State logic)
        animator = build_animator_from_data(
            data,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            default_anim="idle",
        )
        if animator:
            if not (hasattr(data, "animations") and data.animations):
                if "idle" in animator.animations:
                    animator.animations["walk"] = animator.animations["idle"]
            world.add_component(entity, animator)
            # Disable legacy sprite self-animation to avoid conflict?
            # AnimationSystem prioritizes Animator, but Sprite.is_animating might cause double updates?
            # AnimationSystem: if has Animator -> use it. else if Sprite -> use legacy.
            # So it's safe. But best to set is_animating=False if Animator takes over.
            sprite.is_animating = False

        world.add_component(entity, Selectable())
        world.add_component(entity, StableIDComponent(id=world.get_next_stable_id()))
        world.add_component(entity, Persistable())

        # Movement & Visual Components
        movement_controller = MovementController()
        if rm.tuning:
            visuals = rm.tuning.visuals.movement
            movement_controller.bob_height = visuals.bob_height
            movement_controller.bob_speed = visuals.bob_speed
        world.add_component(entity, movement_controller)
        world.add_component(entity, SteeringComponent())
        # Shadow logic: All Yukkuris have shadows but Flandre has special handling via Flight
        world.add_component(entity, VisualTransform(has_drop_shadow=True))


        # Yukkuri Stats and Needs
        stats = YukkuriStats(
            name=f"{type_id}_{entity}",
            type_id=type_id,
            age=age,
            growth_stage=growth_stage,
            agility=_get_attr(data, "agility", 1.0),
        )
        world.add_component(entity, stats)

        needs = Needs(max_health=max_health, health=max_health, hunger=0.0)
        world.add_component(entity, needs)

        # Emotional State
        emotional_state = EmotionalState()
        world.add_component(entity, emotional_state)

        # AI
        world.add_component(entity, AIState())
        world.add_component(entity, GossipQueue())

        # Personality & Relationships
        world.add_component(entity, RelationshipRegistry())

        traits = set()
        axis = PersonalityAxis()

        # Inheritance logic
        if parents and trait_service:
            parent_personalities = [
                p
                for p in (world.try_get_component(pid, Personality) for pid in parents)
                if p
            ]
            if parent_personalities:
                # 50% chance to inherit each trait from parents
                for pp in parent_personalities:
                    for t in pp.traits:
                        if rng.random_float() < 0.5:
                            traits.add(t)

                # Inherit axis values
                total_kindness = sum(pp.axis.kindness for pp in parent_personalities)
                total_energy = sum(pp.axis.energy for pp in parent_personalities)
                total_bravery = sum(pp.axis.bravery for pp in parent_personalities)
                total_greed = sum(pp.axis.greed for pp in parent_personalities)

                count = len(parent_personalities)
                axis.kindness = int(total_kindness / count + rng.uniform(-10, 10))
                axis.energy = int(total_energy / count + rng.uniform(-10, 10))
                axis.bravery = int(total_bravery / count + rng.uniform(-10, 10))
                axis.greed = int(total_greed / count + rng.uniform(-10, 10))

        # Random generation if no parents
        if not parents:
            axis.kindness = int(rng.gauss(0, 30))
            axis.energy = int(rng.gauss(0, 30))
            axis.bravery = int(rng.gauss(0, 30))
            axis.greed = int(rng.gauss(0, 30))

        # Clamp values
        axis.kindness = max(-100, min(100, axis.kindness))
        axis.energy = max(-100, min(100, axis.energy))
        axis.bravery = max(-100, min(100, axis.bravery))
        axis.greed = max(-100, min(100, axis.greed))

        # Random mutation or random trait if none inherited
        if trait_service and (rng.random_float() < 0.1 or not traits):
            all_traits = trait_service.get_all_trait_ids()
            if all_traits:
                traits.add(rng.choice(all_traits))

        # Apply Trait Axis Shifts (Center Shift)
        if trait_service:
            for trait_id in traits:
                t_data = trait_service.get_trait(trait_id)
                if t_data and t_data.axis_shift:
                    shifts = t_data.axis_shift
                    axis.kindness += shifts.get("kindness", 0)
                    axis.energy += shifts.get("energy", 0)
                    axis.bravery += shifts.get("bravery", 0)
                    axis.greed += shifts.get("greed", 0)

        # Re-clamp after shifts
        axis.kindness = max(-100, min(100, axis.kindness))
        axis.energy = max(-100, min(100, axis.energy))
        axis.bravery = max(-100, min(100, axis.bravery))
        axis.greed = max(-100, min(100, axis.greed))

        # Copy axis to base_axis
        base_axis = PersonalityAxis(
            kindness=axis.kindness,
            energy=axis.energy,
            bravery=axis.bravery,
            greed=axis.greed,
        )

        personality = Personality(traits=traits, axis=axis, base_axis=base_axis)
        world.add_component(entity, personality)

        # Initialize Skills
        if skill_service:
            skill_service.initialize_skills(entity)

        # Vision
        world.add_component(entity, Vision(range=300.0, fov=360.0))

        # Mount (Hierarchy Root)
        world.add_component(entity, Mount())

        # Inventory (Reimu and Marisa only)
        if type_id in ("reimu", "marisa"):
            world.add_component(entity, InventoryComponent())

        # Physics
        add_physics_body(
            world=world,
            entity=entity,
            shape_type="circle",
            mass=10.0,
            position=(x, y),
            radius_or_size=radius,
            collision_category=CollisionCategories.GROUND_UNIT,
            collision_mask=CollisionCategories.HIGH_OBSTACLE
            | CollisionCategories.GROUND_UNIT
            | CollisionCategories.POOP,
            elasticity=0.5,
            friction=0.5,
            set_userdata=True,
            body_type=pymunk.Body.KINEMATIC,
        )

        # Flight Component (for flying Yukkuris like Flandre)
        can_fly = _get_attr(data, "can_fly", False)
        if can_fly:
            max_altitude = _get_attr(data, "max_altitude", 60.0)
            fly_stamina = _get_attr(data, "fly_stamina", 100.0)
            flight = Flight(
                altitude=0.0,
                max_altitude=max_altitude,
                stamina=fly_stamina,
                max_stamina=fly_stamina,
                state=FlightState.GROUNDED,
            )
            world.add_component(entity, flight)

        # Predator Component (for predator Yukkuris like Flandre)
        is_predator = _get_attr(data, "is_predator", False)
        if is_predator:
            prey_tags_raw = _get_attr(data, "prey_tags", [])
            prey_tags = set(prey_tags_raw) if prey_tags_raw else set()
            predator = Predator(
                prey_tags=prey_tags,
                prey_sense_radius=_get_attr(data, "prey_sense_radius", 300.0),
                hunger_threshold=_get_attr(data, "hunger_threshold", 60.0),
                aggression=_get_attr(data, "aggression", 1.0),
                dps=_get_attr(data, "dps", 20.0),
            )
            world.add_component(entity, predator)

        return entity

    except Exception:
        world.destroy_entity(entity)
        raise
