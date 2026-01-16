"""
Perception System.
Populates Blackboard components with perception data and social context.
Part of Proposal 4: Unified AI Architecture.
"""

import time
import math
from typing import cast
from ...engine.ecs import System, World
from ...engine.types import EntityID
from ..components import Transform
from ..yukkuri_components import (
    AIState,
    Blackboard,
    TargetInfo,
    LastKnownPosition,
    YukkuriStats,
    Predator,
    RelationshipRegistry,
    ItemStats,
)


class PerceptionSystem(System):
    """
    System that populates Blackboard components with perception data.

    Reads visible_entities from AIState (set by VisibilitySystem) and
    translates them into TargetInfo entries with social context resolution.
    Also manages short-term memory for entities that leave visibility.
    """

    def __init__(self) -> None:
        """Initializes the PerceptionSystem."""
        self.memory_duration = 10.0  # Seconds to remember entities after losing sight

    def update(self, world: World, dt: float) -> None:
        """
        Updates Blackboard components for all entities with both AIState and Blackboard.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        current_time = time.time()

        entities = world.get_components_tuple(AIState, Blackboard, Transform)

        for entity_id, (ai_state, blackboard, trans) in entities:
            self._update_blackboard(
                world, entity_id, ai_state, blackboard, trans, current_time
            )

    def _update_blackboard(
        self,
        world: World,
        entity_id: int,
        ai_state: AIState,
        blackboard: Blackboard,
        trans: Transform,
        current_time: float,
    ) -> None:
        """
        Updates a single entity's Blackboard.
        """
        my_pos = (trans.x, trans.y)

        # Get this entity's components for social context
        my_stats = world.try_get_component(entity_id, YukkuriStats)
        my_predator = world.try_get_component(entity_id, Predator)
        my_relations = world.try_get_component(entity_id, RelationshipRegistry)

        # Track previous visible targets for memory management
        previously_visible = set(blackboard.visible_targets.keys())
        currently_visible: set[EntityID] = set()

        # Reset counts
        blackboard.nearby_friends = 0
        blackboard.nearby_enemies = 0
        blackboard.nearby_prey = 0
        blackboard.closest_threat_id = None
        blackboard.closest_food_id = None

        closest_threat_dist = float("inf")
        closest_food_dist = float("inf")

        # Process visible entities
        for target_id in ai_state.visible_entities:
            target_trans = world.try_get_component(target_id, Transform)
            if not target_trans:
                continue

            target_pos = (target_trans.x, target_trans.y)
            distance = math.hypot(target_pos[0] - my_pos[0], target_pos[1] - my_pos[1])

            # Resolve social context
            relation = self._resolve_relation(
                world, entity_id, target_id, my_stats, my_predator, my_relations
            )

            # Create TargetInfo
            target_info = TargetInfo(
                entity_id=target_id,
                position=target_pos,
                distance=distance,
                relation=relation,
                timestamp=current_time,
            )

            blackboard.visible_targets[target_id] = target_info
            currently_visible.add(target_id)

            # Update counts and closest references
            if relation in ("Friend", "Family"):
                blackboard.nearby_friends += 1
            elif relation in ("Enemy", "Threat"):
                blackboard.nearby_enemies += 1
                if distance < closest_threat_dist:
                    closest_threat_dist = distance
                    blackboard.closest_threat_id = target_id
            elif relation == "Prey":
                blackboard.nearby_prey += 1
                # Prey is potential food for predators
                if distance < closest_food_dist:
                    closest_food_dist = distance
                    blackboard.closest_food_id = target_id

            # Check if target is food item
            target_item = world.try_get_component(target_id, ItemStats)
            if target_item and target_item.nutrition > 0:
                if distance < closest_food_dist:
                    closest_food_dist = distance
                    blackboard.closest_food_id = target_id

        # Move entities that left visibility to short-term memory
        lost_targets = previously_visible - currently_visible
        for lost_id in lost_targets:
            if lost_id in blackboard.visible_targets:
                old_info = blackboard.visible_targets[lost_id]
                blackboard.short_term_memory[lost_id] = LastKnownPosition(
                    position=old_info.position,
                    timestamp=current_time,
                )
                del blackboard.visible_targets[lost_id]

        # Clean up expired memories
        expired_memories = [
            mem_id
            for mem_id, mem in blackboard.short_term_memory.items()
            if current_time - mem.timestamp > self.memory_duration
        ]
        for mem_id in expired_memories:
            del blackboard.short_term_memory[mem_id]

    def _resolve_relation(
        self,
        world: World,
        self_id: int,
        target_id: int,
        my_stats: YukkuriStats | None,
        my_predator: Predator | None,
        my_relations: RelationshipRegistry | None,
    ) -> str:
        """
        Resolves the social relationship between self and target.

        Resolution Order (from Proposal 4 design):
        1. Predator/Prey dynamics (highest priority)
        2. Family relationship
        3. Affinity score
        4. Default to Neutral

        Returns:
            str: One of "Friend", "Enemy", "Neutral", "Prey", "Threat", "Family"
        """
        target_stats = world.try_get_component(target_id, YukkuriStats)
        target_predator = world.try_get_component(target_id, Predator)

        # 1. Predator/Prey Check
        # Am I a predator looking at prey?
        if my_predator and target_stats:
            if target_stats.type_id in my_predator.prey_tags:
                return "Prey"

        # Is target a predator that hunts my type?
        if target_predator and my_stats:
            if my_stats.type_id in target_predator.prey_tags:
                return "Threat"

        # 2. Family Check
        if my_relations:
            # Check if target is family
            if target_id in my_relations.biological_parents:
                return "Family"
            if target_id in my_relations.biological_children:
                return "Family"
            if my_relations.mate_id == target_id:
                return "Family"
            if my_relations.family_group_id and target_stats:
                target_relations = world.try_get_component(
                    target_id, RelationshipRegistry
                )
                if (
                    target_relations
                    and target_relations.family_group_id == my_relations.family_group_id
                ):
                    return "Family"

            # 3. Affinity Check
            if cast(EntityID, target_id) in my_relations.relationships:
                rel_data = my_relations.relationships[cast(EntityID, target_id)]
                if rel_data.affinity > 50:
                    return "Friend"
                elif rel_data.affinity < -10:
                    return "Enemy"

        # 4. Default
        return "Neutral"
