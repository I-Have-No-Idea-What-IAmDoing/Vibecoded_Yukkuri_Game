"""
Prefab functions for Yukkuri entities.
"""

from typing import Optional, List, Any
import random
import pymunk

from ...engine.ecs import World
from ...engine.resource_manager import ResourceManager
from ..components import (
    Transform,
    Sprite,
    Selectable,
    MovementController,
    VisualTransform,
    Vision,
    Mount,
)
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    AIState,
    Personality,
    RelationshipRegistry,
    EmotionalState,
    PersonalityAxis,
    GossipQueue,
)
from ..components_persistence import StableIDComponent, Persistable
from ..collision_constants import CollisionCategories
from ..trait_service import TraitService
from ..skill_service import SkillService
from ..systems.physics import PhysicsSystem
from ..physics_utils import add_physics_body, get_yukkuri_radius


def create_yukkuri(
    world: World,
    type_id: str,
    x: float,
    y: float,
    age: float = 0.0,
    parents: Optional[List[int]] = None,
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
    physics_system = world.services.try_get(PhysicsSystem)
    trait_service = world.services.try_get(TraitService)
    skill_service = world.services.try_get(SkillService)

    data = rm.yukkuri_types.get(type_id)
    if not data:
        raise ValueError(f"Unknown yukkuri type: {type_id}")

    entity = world.create_entity()

    def _get_attr(d: Any, k: str, default: Any = None) -> Any:
        if isinstance(d, dict):
            return d.get(k, default)
        return getattr(d, k, default)

    image = _get_attr(data, "image", "yukkuri_default.png")
    width = _get_attr(data, "width", 64)
    height = _get_attr(data, "height", 64)
    max_health = _get_attr(data, "max_health", 100)

    # Determine growth stage and scale based on age
    scale = 1.0
    growth_stage = "Baby"

    if age >= 300:
        growth_stage = "Adult"
        scale = 1.0
    elif age >= 100:
        growth_stage = "Child"
        scale = 0.75
    else:
        growth_stage = "Baby"
        scale = 0.5
        max_health *= 0.5

    radius = get_yukkuri_radius(growth_stage)

    frame_count = _get_attr(data, "frame_count", 1)
    frame_duration = _get_attr(data, "frame_duration", 0.1)
    loop = _get_attr(data, "loop", True)

    # Core Components
    world.add_component(entity, Transform(x=x, y=y, scale=scale))
    world.add_component(
        entity,
        Sprite(
            image_name=image,
            width=width,
            height=height,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            is_animating=(frame_count > 1),
        ),
    )
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
    world.add_component(entity, VisualTransform())

    # Yukkuri Stats and Needs
    stats = YukkuriStats(
        name=f"{type_id}_{entity}", type_id=type_id, age=age, growth_stage=growth_stage
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
            p for p in (world.get_component(pid, Personality) for pid in parents) if p
        ]
        if parent_personalities:
            # 50% chance to inherit each trait from parents
            for pp in parent_personalities:
                for t in pp.traits:
                    if random.random() < 0.5:
                        traits.add(t)

            # Inherit axis values
            total_kindness = sum(pp.axis.kindness for pp in parent_personalities)
            total_energy = sum(pp.axis.energy for pp in parent_personalities)
            total_bravery = sum(pp.axis.bravery for pp in parent_personalities)
            total_greed = sum(pp.axis.greed for pp in parent_personalities)

            count = len(parent_personalities)
            axis.kindness = int(total_kindness / count + random.uniform(-10, 10))
            axis.energy = int(total_energy / count + random.uniform(-10, 10))
            axis.bravery = int(total_bravery / count + random.uniform(-10, 10))
            axis.greed = int(total_greed / count + random.uniform(-10, 10))

    # Random generation if no parents
    if not parents:
        axis.kindness = int(random.gauss(0, 30))
        axis.energy = int(random.gauss(0, 30))
        axis.bravery = int(random.gauss(0, 30))
        axis.greed = int(random.gauss(0, 30))

    # Clamp values
    axis.kindness = max(-100, min(100, axis.kindness))
    axis.energy = max(-100, min(100, axis.energy))
    axis.bravery = max(-100, min(100, axis.bravery))
    axis.greed = max(-100, min(100, axis.greed))

    # Random mutation or random trait if none inherited
    if trait_service and (random.random() < 0.1 or not traits):
        all_traits = trait_service.get_all_trait_ids()
        if all_traits:
            traits.add(random.choice(all_traits))

    # Apply Trait Axis Shifts (Center Shift)
    if trait_service:
        for trait_id in traits:
            t_data = trait_service.get_trait(trait_id)
            if t_data:
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

    # Physics
    add_physics_body(
        world=world,
        entity=entity,
        shape_type="circle",
        mass=10.0,
        position=(x, y),
        radius_or_size=radius,
        collision_category=CollisionCategories.YUKKURI,
        collision_mask=CollisionCategories.WALL
        | CollisionCategories.YUKKURI
        | CollisionCategories.POOP,
        elasticity=0.5,
        friction=0.5,
        set_userdata=True,
        body_type=pymunk.Body.KINEMATIC,
    )

    return entity
