"""
Family System - "Take It Easy Together" Mechanics.

Manages family group formation, maintenance, and cooperative benefits.
Implements the core social bonding mechanic where Yukkuris form lasting
family units and share resources.

Family Formation:
-   High affinity + trust pairs automatically form new families.
-   Existing families can absorb new members meeting thresholds.
-   Family bonds persist until manually dissolved or death.

Family Benefits (when family members are nearby):
-   Passive happiness/stress bonuses.
-   Food sharing: Eating members share nutrition with hungry family.
-   Nest sharing: Sleeping members provide rest bonuses to family.

Performance:
-   Uses SpatialService spatial partitioning when available.
-   Falls back to O(N²) comparison without spatial indexing.
"""

from typing import cast

from loguru import logger

from ...engine import rng
from ...engine.ecs import System, World
from ...engine.types import EntityID
from ..components import (
    AIState,
    EmotionalState,
    Needs,
    RelationshipRegistry,
    YukkuriStats,
)
from ...engine.components import (
    Transform,
)
from ...engine.protocols import ISpatialService


class FamilySystem(System):
    """
    System responsible for managing family groups and logic.

    Attributes:
        check_interval (float): Time interval between family logic checks.
        last_check (float): Time since last check.
    """

    # FORMATION THRESHOLDS
    # Both affinity AND trust must exceed these to form/join a family
    MIN_AFFINITY_FOR_FAMILY = 80.0
    MIN_TRUST_FOR_FAMILY = 80.0

    # PROXIMITY SETTINGS
    BENEFIT_RANGE = 150.0  # Maximum distance for benefits (pixels)
    BENEFIT_RANGE_SQ = BENEFIT_RANGE * BENEFIT_RANGE

    # TOGETHERNESS BONUSES
    # Applied per update tick while family members are near each other
    BASE_HAPPINESS_GAIN = 0.5
    BASE_STRESS_REDUCTION = 0.5

    # FOOD SHARING
    # When one member eats, hungry family nearby gets partial benefit
    FOOD_SHARING_HUNGER_THRESHOLD = 50.0  # Other must be this hungry to receive
    FOOD_SHARING_AMOUNT = 1.0  # Hunger points reduced for recipient

    # NEST SHARING
    # When one member sleeps, nearby family gets rest bonus
    SLEEP_ENERGY_GAIN = 0.5
    SLEEP_STRESS_REDUCTION = 1.0

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
        """
        entities = world.get_components_tuple(RelationshipRegistry, YukkuriStats)

        for entity, (registry, stats) in entities:
            if not registry or not stats:
                continue

            # Look for high affinity/trust partners
            for other_id, rel in registry.relationships.items():
                if (
                    rel.affinity > self.MIN_AFFINITY_FOR_FAMILY
                    and rel.trust > self.MIN_TRUST_FOR_FAMILY
                ):
                    # Potential mate or family member
                    other_registry = world.try_get_component(other_id, RelationshipRegistry)
                    if not other_registry:
                        continue

                    # Case 1: Neither has a family -> Create new family
                    if (
                        registry.family_group_id is None
                        and other_registry.family_group_id is None
                    ):
                        new_family_id_int = rng.getrandbits(32)
                        new_family_id = cast(EntityID, new_family_id_int)
                        registry.family_group_id = new_family_id
                        other_registry.family_group_id = new_family_id
                        logger.info(
                            f"New Family Formed: {stats.name} and Entity {other_id}"
                        )

                    # Case 2: One has family, other doesn't -> Join existing
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
        """
        spatial_service = world.services.try_get(ISpatialService)

        if spatial_service:
            self._process_benefits_with_sectors(world, spatial_service)
        else:
            # O(N²) fallback - slow for large populations.
            self._process_benefits_fallback(world)

    def _process_benefits_with_sectors(
        self, world: World, spatial_service: ISpatialService
    ) -> None:
        """
        Process family benefits using spatial partitioning for efficiency.

        Args:
            world (World): The ECS World.
            spatial_service (ISpatialService): The sector map service.
        """
        entities = world.get_components_tuple(
            RelationshipRegistry, YukkuriStats, Needs, Transform, AIState
        )

        for eid, (reg, stats, needs, trans, ai) in entities:
            if reg is None or reg.family_group_id is None:
                continue

            emotional = world.try_get_component(eid, EmotionalState)

            if stats is None or needs is None or trans is None or ai is None:
                continue

            # Sector queries cover ~1500x1500 area, reducing checks vs O(N²).
            neighbors = spatial_service.get_entities_in_range(trans.x, trans.y, "visual")

            for other_eid in neighbors:
                if other_eid <= eid:  # Avoid duplicate pairs and self.
                    continue

                other_reg = world.try_get_component(other_eid, RelationshipRegistry)
                if (
                    other_reg is None
                    or other_reg.family_group_id != reg.family_group_id
                ):
                    continue

                other_trans = world.try_get_component(other_eid, Transform)
                other_ai = world.try_get_component(other_eid, AIState)
                other_stats = world.try_get_component(other_eid, YukkuriStats)
                other_needs = world.try_get_component(other_eid, Needs)
                other_emotional = world.try_get_component(other_eid, EmotionalState)

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
        """
        entities = world.get_components_tuple(
            RelationshipRegistry, YukkuriStats, Needs, Transform, AIState
        )

        for i, (eid, (reg, stats, needs, trans, ai)) in enumerate(entities):
            if reg is None or reg.family_group_id is None:
                continue

            emotional = world.try_get_component(eid, EmotionalState)

            if stats is None or needs is None or trans is None or ai is None:
                continue

            for j in range(i + 1, len(entities)):
                other_eid, (other_reg, other_stats, other_needs, other_trans, other_ai) = entities[j]

                if (
                    other_reg is None
                    or other_reg.family_group_id != reg.family_group_id
                ):
                    continue

                other_emotional = world.try_get_component(other_eid, EmotionalState)

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
        trans: Transform,
        other_trans: Transform,
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
            emotional (EmotionalState | None): First entity emotional state.
            other_emotional (EmotionalState | None): Second entity emotional state.
        """
        dist_sq = (trans.x - other_trans.x) ** 2 + (trans.y - other_trans.y) ** 2
        if dist_sq < self.BENEFIT_RANGE_SQ:
            # 1. Base "Together" Happiness
            if emotional:
                emotional.adjust_happiness(self.BASE_HAPPINESS_GAIN)
                emotional.adjust_stress(-self.BASE_STRESS_REDUCTION)
            if other_emotional:
                other_emotional.adjust_happiness(self.BASE_HAPPINESS_GAIN)
                other_emotional.adjust_stress(-self.BASE_STRESS_REDUCTION)

            # 2. Food sharing: one eating shares with hungry partner.
            if (
                ai.current_action == "Eat"
                and other_needs.hunger > self.FOOD_SHARING_HUNGER_THRESHOLD
            ):
                other_needs.adjust_hunger(-self.FOOD_SHARING_AMOUNT)
                if other_emotional:
                    other_emotional.adjust_happiness(self.BASE_HAPPINESS_GAIN)
                logger.debug(
                    f"Family Share: {stats.name} sharing food with {other_stats.name}"
                )

            elif (
                other_ai.current_action == "Eat"
                and needs.hunger > self.FOOD_SHARING_HUNGER_THRESHOLD
            ):
                needs.adjust_hunger(-self.FOOD_SHARING_AMOUNT)
                if emotional:
                    emotional.adjust_happiness(self.BASE_HAPPINESS_GAIN)
                logger.debug(
                    f"Family Share: {other_stats.name} sharing food with {stats.name}"
                )

            # 3. Nest sharing: sleeping member boosts nearby partner's recovery.
            if ai.current_action == "Sleep":
                other_needs.adjust_energy(self.SLEEP_ENERGY_GAIN)
                if other_emotional:
                    other_emotional.adjust_stress(-self.SLEEP_STRESS_REDUCTION)

            if other_ai.current_action == "Sleep":
                needs.adjust_energy(self.SLEEP_ENERGY_GAIN)
                if emotional:
                    emotional.adjust_stress(-self.SLEEP_STRESS_REDUCTION)
