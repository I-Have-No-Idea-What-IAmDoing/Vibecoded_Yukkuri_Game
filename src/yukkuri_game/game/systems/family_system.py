"""
Module defining the FamilySystem logic.
"""

import random
from loguru import logger

from ...engine.ecs import System, World
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    RelationshipRegistry,
    AIState,
    EmotionalState,
)
from ..systems.sector_system import SectorMap
from ..components import Transform
from ...engine.types import EntityID
from typing import cast


class FamilySystem(System):
    """
    System responsible for managing family groups and logic.
    Handles 'Take it easy together' logic:
    - High affinity entities forming a family.
    - Resource sharing (food/nest benefits).

    Attributes:
        check_interval (float): Time interval between family logic checks.
        last_check (float): Time since last check.
    """

    def __init__(self) -> None:
        """Initializes the FamilySystem."""
        super().__init__()
        self.check_interval = 2.0  # Check more frequently for resource sharing
        self.last_check = 0.0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the FamilySystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self.last_check += dt
        if self.last_check >= self.check_interval:
            self.last_check = 0.0
            self._process_family_formation(world)
            self._process_family_benefits(world)

    def _process_family_formation(self, world: World) -> None:
        """
        Check for high affinity pairs that are not in a family and merge them.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        entities = world.get_entities_with(RelationshipRegistry, YukkuriStats)

        for entity in entities:
            registry = world.get_component(entity, RelationshipRegistry)
            stats = world.get_component(entity, YukkuriStats)

            if not registry or not stats:
                continue

            # Look for high affinity/trust partners
            for other_id, rel in registry.relationships.items():
                if rel.affinity > 80.0 and rel.trust > 80.0:
                    # Potential mate or family member
                    other_registry = world.get_component(other_id, RelationshipRegistry)
                    if not other_registry:
                        continue

                    # If neither has a family, create one
                    if (
                        registry.family_group_id is None
                        and other_registry.family_group_id is None
                    ):
                        # Use deterministic random bits
                        new_family_id_int = random.getrandbits(32)
                        new_family_id = cast(EntityID, new_family_id_int)
                        registry.family_group_id = new_family_id
                        other_registry.family_group_id = new_family_id
                        logger.info(
                            f"New Family Formed: {stats.name} and Entity {other_id}"
                        )

                    # If one has a family and other doesn't, join
                    elif (
                        registry.family_group_id is not None
                        and other_registry.family_group_id is None
                    ):
                        other_registry.family_group_id = registry.family_group_id
                        logger.info(f"Entity {other_id} joined family of {stats.name}")

                    elif (
                        registry.family_group_id is None
                        and other_registry.family_group_id is not None
                    ):
                        registry.family_group_id = other_registry.family_group_id
                        logger.info(f"{stats.name} joined family of Entity {other_id}")

    def _process_family_benefits(self, world: World) -> None:
        """
        Apply benefits to family members near each other.
        Includes simulated resource sharing.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """

        sector_map = world.services.try_get(SectorMap)

        if sector_map:
            # Optimization: Use SectorMap if available
            self._process_benefits_with_sectors(world, sector_map)
        else:
            # Fallback to O(N^2) checks if SectorMap isn't available.
            # This compares every entity against every other entity, which is slow for large populations.
            self._process_benefits_fallback(world)

    def _process_benefits_with_sectors(
        self, world: World, sector_map: SectorMap
    ) -> None:
        """
        Process family benefits using spatial partitioning for efficiency.

        Args:
            world (World): The ECS World.
            sector_map (SectorMap): The sector map service.

        Returns:
            None
        """
        from ..components import Transform

        entities = world.get_entities_with(
            RelationshipRegistry, YukkuriStats, Needs, Transform, AIState
        )

        # To avoid processing pairs twice, we only process if eid < other_eid.
        # But sector queries return neighbors, so we just filter.

        for eid in entities:
            reg = world.get_component(eid, RelationshipRegistry)
            if reg is None or reg.family_group_id is None:
                continue

            stats = world.get_component(eid, YukkuriStats)
            needs = world.get_component(eid, Needs)
            trans = world.get_component(eid, Transform)
            ai = world.get_component(eid, AIState)
            emotional = world.get_component(eid, EmotionalState)

            if stats is None or needs is None or trans is None or ai is None:
                continue

            # Get neighbors (Visual range includes adjacent sectors which is usually enough for 150px)
            # Sector size is 500, so "Same + Adjacent" covers 1500x1500 area centered on sector.
            # This drastically reduces the number of checks compared to O(N^2).
            neighbors = sector_map.get_entities_in_range(trans.x, trans.y, "visual")

            for other_eid in neighbors:
                if other_eid <= eid:  # Ensure unique pair (A, B) and avoid (A, A)
                    continue

                # Check components existence for neighbor
                # Optimization: We could use `world.has_components` but retrieving them checks anyway.
                other_reg = world.get_component(other_eid, RelationshipRegistry)
                if (
                    other_reg is None
                    or other_reg.family_group_id != reg.family_group_id
                ):
                    continue

                other_trans = world.get_component(other_eid, Transform)
                other_ai = world.get_component(other_eid, AIState)
                other_stats = world.get_component(other_eid, YukkuriStats)
                other_needs = world.get_component(other_eid, Needs)
                other_emotional = world.get_component(other_eid, EmotionalState)

                if (
                    other_trans is None
                    or other_ai is None
                    or other_stats is None
                    or other_needs is None
                ):
                    continue

                self._apply_benefit_pair(
                    eid,
                    other_eid,
                    stats,
                    other_stats,
                    needs,
                    other_needs,
                    trans,
                    other_trans,
                    ai,
                    other_ai,
                    emotional,
                    other_emotional,
                )

    def _process_benefits_fallback(self, world: World) -> None:
        """
        Process family benefits using O(N^2) checks (fallback).

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        from ..components import Transform

        entities = world.get_entities_with(
            RelationshipRegistry, YukkuriStats, Needs, Transform, AIState
        )

        for i, eid in enumerate(entities):
            reg = world.get_component(eid, RelationshipRegistry)
            if reg is None or reg.family_group_id is None:
                continue

            stats = world.get_component(eid, YukkuriStats)
            needs = world.get_component(eid, Needs)
            trans = world.get_component(eid, Transform)
            ai = world.get_component(eid, AIState)
            emotional = world.get_component(eid, EmotionalState)

            if stats is None or needs is None or trans is None or ai is None:
                continue

            for j in range(i + 1, len(entities)):
                other_eid = entities[j]
                other_reg = world.get_component(other_eid, RelationshipRegistry)

                if (
                    other_reg is None
                    or other_reg.family_group_id != reg.family_group_id
                ):
                    continue

                # Same family
                other_trans = world.get_component(other_eid, Transform)
                other_ai = world.get_component(other_eid, AIState)
                other_stats = world.get_component(other_eid, YukkuriStats)
                other_needs = world.get_component(other_eid, Needs)
                other_emotional = world.get_component(other_eid, EmotionalState)

                if (
                    other_trans is None
                    or other_ai is None
                    or other_stats is None
                    or other_needs is None
                ):
                    continue

                self._apply_benefit_pair(
                    eid,
                    other_eid,
                    stats,
                    other_stats,
                    needs,
                    other_needs,
                    trans,
                    other_trans,
                    ai,
                    other_ai,
                    emotional,
                    other_emotional,
                )

    def _apply_benefit_pair(
        self,
        eid: int,
        other_eid: int,
        stats: YukkuriStats,
        other_stats: YukkuriStats,
        needs: Needs,
        other_needs: Needs,
        trans: "Transform",
        other_trans: "Transform",
        ai: AIState,
        other_ai: AIState,
        emotional: EmotionalState | None,
        other_emotional: EmotionalState | None,
    ) -> None:
        """
        Helper to apply benefits between two entities if they are close enough.

        Args:
            eid (int): First entity ID.
            other_eid (int): Second entity ID.
            stats (YukkuriStats): First entity stats.
            other_stats (YukkuriStats): Second entity stats.
            needs (Needs): First entity needs.
            other_needs (Needs): Second entity needs.
            trans (Transform): First entity transform.
            other_trans (Transform): Second entity transform.
            ai (AIState): First entity AI state.
            other_ai (AIState): Second entity AI state.
            emotional (Optional[EmotionalState]): First entity emotional state.
            other_emotional (Optional[EmotionalState]): Second entity emotional state.

        Returns:
            None
        """

        dist_sq = (trans.x - other_trans.x) ** 2 + (trans.y - other_trans.y) ** 2
        if dist_sq < 150 * 150:  # Range for family benefits
            # 1. Base "Together" Happiness
            if emotional:
                emotional.happiness = min(100.0, emotional.happiness + 0.5)
                emotional.stress = max(0.0, emotional.stress - 0.5)
            if other_emotional:
                other_emotional.happiness = min(100.0, other_emotional.happiness + 0.5)
                other_emotional.stress = max(0.0, other_emotional.stress - 0.5)

            # 2. Resource Sharing: Food
            # If one is eating, share nutrition/happiness with hungry partner
            # (Simulates "Here, have some" or calling to food)
            if ai.current_action == "Eat" and other_needs.hunger > 50.0:
                other_needs.hunger = max(
                    0.0, other_needs.hunger - 1.0
                )  # Share small benefit
                if other_emotional:
                    other_emotional.happiness = min(
                        100.0, other_emotional.happiness + 0.5
                    )
                logger.debug(
                    f"Family Share: {stats.name} sharing food with {other_stats.name}"
                )

            elif other_ai.current_action == "Eat" and needs.hunger > 50.0:
                needs.hunger = max(0.0, needs.hunger - 1.0)
                if emotional:
                    emotional.happiness = min(100.0, emotional.happiness + 0.5)
                logger.debug(
                    f"Family Share: {other_stats.name} sharing food with {stats.name}"
                )

            # 3. Resource Sharing: Nest/Sleep
            # If one is sleeping, boost comfort/recovery for nearby partner (simulating shared nest)
            if ai.current_action == "Sleep":
                other_needs.energy = min(100.0, other_needs.energy + 0.5)
                if other_emotional:
                    other_emotional.stress = max(0.0, other_emotional.stress - 1.0)

            if other_ai.current_action == "Sleep":
                needs.energy = min(100.0, needs.energy + 0.5)
                if emotional:
                    emotional.stress = max(0.0, emotional.stress - 1.0)
