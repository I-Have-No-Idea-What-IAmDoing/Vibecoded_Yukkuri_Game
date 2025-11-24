"""
Module defining the FamilySystem logic.
"""
from typing import List, Optional
import time
import random
from loguru import logger

from ...engine.ecs import System, World
from ..services import TimeService
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData, AIState

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

    def __init__(self):
        """Initializes the FamilySystem."""
        super().__init__()
        self.check_interval = 2.0 # Check more frequently for resource sharing
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

    def _process_family_formation(self, world: World):
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
                    if registry.family_group_id is None and other_registry.family_group_id is None:
                        # Use deterministic random bits
                        new_family_id = random.getrandbits(32)
                        registry.family_group_id = new_family_id
                        other_registry.family_group_id = new_family_id
                        logger.info(f"New Family Formed: {stats.name} and Entity {other_id}")

                    # If one has a family and other doesn't, join
                    elif registry.family_group_id is not None and other_registry.family_group_id is None:
                        other_registry.family_group_id = registry.family_group_id
                        logger.info(f"Entity {other_id} joined family of {stats.name}")

                    elif registry.family_group_id is None and other_registry.family_group_id is not None:
                        registry.family_group_id = other_registry.family_group_id
                        logger.info(f"{stats.name} joined family of Entity {other_id}")

    def _process_family_benefits(self, world: World):
        """
        Apply benefits to family members near each other.
        Includes simulated resource sharing.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        from ..components import Transform

        # Optimization: Quadtree or spatial hash would be better, but O(N^2) for small N is fine
        entities = world.get_entities_with(RelationshipRegistry, YukkuriStats, Transform, AIState)

        for i, eid in enumerate(entities):
            reg = world.get_component(eid, RelationshipRegistry)
            if reg.family_group_id is None:
                continue

            stats = world.get_component(eid, YukkuriStats)
            trans = world.get_component(eid, Transform)
            ai = world.get_component(eid, AIState)

            for j in range(i + 1, len(entities)):
                other_eid = entities[j]
                other_reg = world.get_component(other_eid, RelationshipRegistry)

                if other_reg.family_group_id == reg.family_group_id:
                    # Same family
                    other_trans = world.get_component(other_eid, Transform)
                    other_ai = world.get_component(other_eid, AIState)
                    other_stats = world.get_component(other_eid, YukkuriStats)

                    dist_sq = (trans.x - other_trans.x)**2 + (trans.y - other_trans.y)**2
                    if dist_sq < 150 * 150: # Range for family benefits

                        # 1. Base "Together" Happiness
                        stats.happiness = min(100.0, stats.happiness + 0.5)
                        stats.stress = max(0.0, stats.stress - 0.5)
                        other_stats.happiness = min(100.0, other_stats.happiness + 0.5)
                        other_stats.stress = max(0.0, other_stats.stress - 0.5)

                        # 2. Resource Sharing: Food
                        # If one is eating, share nutrition/happiness with hungry partner
                        # (Simulates "Here, have some" or calling to food)
                        if ai.current_action == "Eat" and other_stats.hunger > 50.0:
                             other_stats.hunger = max(0.0, other_stats.hunger - 1.0) # Share small benefit
                             other_stats.happiness += 0.5
                             logger.debug(f"Family Share: {stats.name} sharing food with {other_stats.name}")

                        elif other_ai.current_action == "Eat" and stats.hunger > 50.0:
                             stats.hunger = max(0.0, stats.hunger - 1.0)
                             stats.happiness += 0.5
                             logger.debug(f"Family Share: {other_stats.name} sharing food with {stats.name}")

                        # 3. Resource Sharing: Nest/Sleep
                        # If one is sleeping, boost comfort/recovery for nearby partner (simulating shared nest)
                        if ai.current_action == "Sleep":
                            other_stats.energy = min(100.0, other_stats.energy + 0.5)
                            other_stats.stress = max(0.0, other_stats.stress - 1.0)

                        if other_ai.current_action == "Sleep":
                            stats.energy = min(100.0, stats.energy + 0.5)
                            stats.stress = max(0.0, stats.stress - 1.0)
