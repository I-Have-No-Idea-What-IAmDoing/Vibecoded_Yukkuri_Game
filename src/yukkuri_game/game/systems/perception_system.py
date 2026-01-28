"""
Perception System - AI Awareness and Social Context.

Populates Blackboard components with perception data from the visibility system.
Translates raw visible entity sets into semantic context (TargetInfo).

Responsibilities:
-   Converts visible entity IDs into `TargetInfo` objects.
-   Resolves relationships (Friend, Enemy, Prey, Family) based on stats and history.
-   Manages Short-Term Memory (remembering entities that just left view).
-   Aggregates census data (count of nearby friends/enemies) for Utility AI.

Relationship Resolution Priority:
1.  Predator/Prey (Biological imperative).
2.  Family (Social bond).
3.  Affinity (Personal history).
4.  Neutral (Default).
"""

import math
from typing import cast

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import EntityDestroyedEvent
from ...engine.types import EntityID
from ..components import Transform
from ..yukkuri_components import (
    AIState,
    Blackboard,
    ItemStats,
    LastKnownPosition,
    Predator,
    RelationshipRegistry,
    TargetInfo,
    YukkuriStats,
)


class PerceptionSystem(System):
    """
    System that populates Blackboard components with perception data.

    Reads `visible_entities` from `AIState` (populated by VisibilitySystem) and
    updates the `Blackboard` component. This separates the "what can I see" logic
    from the "what does it mean to me" logic.

    Attributes:
        _last_update_times (dict[int, float]): Timestamp of last update per entity.
        _last_visible_set_ids (dict[int, int]): ID of the visible entity set from the last frame.
        _subscribed (bool): Whether the system has subscribed to event bus events.
    """

    # Duration (seconds) to remember entities after they leave FOV
    MEMORY_DURATION = 10.0

    # Relationship thresholds
    FRIEND_AFFINITY_THRESHOLD = 50.0
    ENEMY_AFFINITY_THRESHOLD = -10.0

    # Throttle: 10 updates/sec max per entity
    UPDATE_INTERVAL = 0.1

    def __init__(self) -> None:
        """Initializes the PerceptionSystem."""
        super().__init__()
        self._last_update_times: dict[int, float] = {}
        self._last_visible_set_ids: dict[int, int] = {}
        self._subscribed = False

    def initialize(self, world: World | None = None) -> None:
        """
        Sets up event subscriptions.

        Args:
            world (World | None): The ECS World.
        """
        target_world = world
        if target_world is None and hasattr(self, "ecs_world"):
            target_world = self.ecs_world

        if target_world:
            event_bus = target_world.services.try_get(EventBus)
            if event_bus:
                event_bus.subscribe(EntityDestroyedEvent, self.on_entity_destroyed)
                self._subscribed = True

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        """
        Cleans up tracking data for destroyed entities.

        Args:
            event (EntityDestroyedEvent): The destruction event.
        """
        entity_id = event.entity_id
        self._last_update_times.pop(entity_id, None)
        self._last_visible_set_ids.pop(entity_id, None)

    def update(self, world: World, dt: float) -> None:
        """
        Updates perception state for all AI entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self._subscribed:
            self.initialize(world)

        current_time = world.time

        # Iterate entities that have AI + Blackboard + Transform
        entities = world.get_components_tuple(AIState, Blackboard, Transform)

        for entity_id, (ai_state, blackboard, trans) in entities:
            # Throttling Logic:
            # Update if timer expired OR if the set of visible entities has changed physically
            # (checked via object ID, assuming VisibilitySystem replaces the set on change).

            # Fix: Ensure current_visible_id is defined (it was missing in original code)
            visible_set_id = id(ai_state.visible_entities)

            time_expired = (
                current_time - self._last_update_times.get(entity_id, 0.0)
                >= self.UPDATE_INTERVAL
            )
            visibility_changed = visible_set_id != self._last_visible_set_ids.get(
                entity_id, 0
            )

            should_update = time_expired or visibility_changed

            if should_update:
                self._update_blackboard(
                    world, entity_id, ai_state, blackboard, trans, current_time
                )
                self._last_update_times[entity_id] = current_time
                self._last_visible_set_ids[entity_id] = visible_set_id

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
        Populates the Blackboard with analyzed targets.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity ID.
            ai_state (AIState): The AI state component.
            blackboard (Blackboard): The blackboard component.
            trans (Transform): The transform component.
            current_time (float): The current simulation time.
        """
        my_pos = (trans.x, trans.y)

        # Context components
        my_stats = world.try_get_component(entity_id, YukkuriStats)
        my_predator = world.try_get_component(entity_id, Predator)
        my_relations = world.try_get_component(entity_id, RelationshipRegistry)

        # Reaction Time (Agility)
        reaction_delay = 0.5
        if my_stats and my_stats.agility > 0:
            reaction_delay = 0.5 / my_stats.agility

        # Memory management
        previously_visible = set(blackboard.visible_targets.keys())
        currently_visible: set[EntityID] = set()

        # Reset Census
        blackboard.nearby_friends = 0
        blackboard.nearby_enemies = 0
        blackboard.nearby_prey = 0
        blackboard.closest_threat_id = None
        blackboard.closest_food_id = None

        closest_threat_dist = float("inf")
        closest_food_dist = float("inf")

        # Analyze current view
        for target_id in ai_state.visible_entities:
            target_trans = world.try_get_component(target_id, Transform)
            if not target_trans:
                continue

            target_pos = (target_trans.x, target_trans.y)
            distance = math.hypot(target_pos[0] - my_pos[0], target_pos[1] - my_pos[1])

            relation = self._resolve_relation(
                world, entity_id, target_id, my_stats, my_predator, my_relations
            )

            # Persistence: Keep original detection time if known
            old_info = blackboard.visible_targets.get(target_id)
            detected_at = current_time
            if old_info:
                detected_at = old_info.detected_at

            # Update/Create Info
            target_info = TargetInfo(
                entity_id=target_id,
                position=target_pos,
                distance=distance,
                relation=relation,
                timestamp=current_time,
                detected_at=detected_at,
            )

            blackboard.visible_targets[target_id] = target_info
            currently_visible.add(target_id)

            # Reaction Buffering:
            # AI ignores the target for census purposes until reaction time has passed.
            if (current_time - detected_at) < reaction_delay:
                continue

            # Update Census Data
            if relation in ("Friend", "Family"):
                blackboard.nearby_friends += 1
            elif relation in ("Enemy", "Threat"):
                blackboard.nearby_enemies += 1
                if distance < closest_threat_dist:
                    closest_threat_dist = distance
                    blackboard.closest_threat_id = target_id
            elif relation == "Prey":
                blackboard.nearby_prey += 1
                if distance < closest_food_dist:
                    closest_food_dist = distance
                    blackboard.closest_food_id = target_id

            # Food Item Check
            target_item = world.try_get_component(target_id, ItemStats)
            if target_item and target_item.nutrition > 0:
                if distance < closest_food_dist:
                    closest_food_dist = distance
                    blackboard.closest_food_id = target_id

        # Handle entities leaving view (Short-term Memory)
        lost_targets = previously_visible - currently_visible
        for lost_id in lost_targets:
            if lost_id in blackboard.visible_targets:
                old_info = blackboard.visible_targets[lost_id]
                blackboard.short_term_memory[lost_id] = LastKnownPosition(
                    position=old_info.position,
                    timestamp=current_time,
                )
                del blackboard.visible_targets[lost_id]

        # Forget old memories
        expired_memories = [
            mem_id
            for mem_id, mem in blackboard.short_term_memory.items()
            if current_time - mem.timestamp > self.MEMORY_DURATION
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
        Determines the social stance towards a target.

        Args:
            world (World): The ECS World.
            self_id (int): The entity ID of the observer.
            target_id (int): The entity ID of the target.
            my_stats (YukkuriStats | None): The observer's stats.
            my_predator (Predator | None): The observer's predator component.
            my_relations (RelationshipRegistry | None): The observer's relationship registry.

        Returns:
            str: "Friend", "Enemy", "Neutral", "Prey", "Threat", or "Family".
        """
        target_stats = world.try_get_component(target_id, YukkuriStats)
        target_predator = world.try_get_component(target_id, Predator)

        # 1. Biological (Predator/Prey)
        if my_predator and target_stats:
            if target_stats.type_id in my_predator.prey_tags:
                return "Prey"

        if target_predator and my_stats:
            if my_stats.type_id in target_predator.prey_tags:
                return "Threat"

        # 2. Family
        if my_relations:
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

            # 3. Affinity
            if cast(EntityID, target_id) in my_relations.relationships:
                rel_data = my_relations.relationships[cast(EntityID, target_id)]
                if rel_data.affinity > self.FRIEND_AFFINITY_THRESHOLD:
                    return "Friend"
                elif rel_data.affinity < self.ENEMY_AFFINITY_THRESHOLD:
                    return "Enemy"

        # 4. Default
        return "Neutral"
