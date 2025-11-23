from typing import List, Optional
import time
from loguru import logger

from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData

class FamilySystem(System):
    """
    System responsible for managing family groups and logic.
    Handles 'Take it easy together' logic:
    - High affinity entities forming a family.
    - Sharing knowledge (conceptually).
    - Preventing in-fighting.
    """

    def __init__(self):
        super().__init__()
        self.check_interval = 10.0 # Check every 10 seconds
        self.last_check = 0.0

    def update(self, world: World, dt: float) -> None:
        self.last_check += dt
        if self.last_check >= self.check_interval:
            self.last_check = 0.0
            self._process_family_formation(world)
            self._process_family_benefits(world)

    def _process_family_formation(self, world: World):
        """
        Check for high affinity pairs that are not in a family and merge them.
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
                        new_family_id = int(time.time() * 1000) # Simple ID generation
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
        """
        # For MVP, just a happiness boost if near family members
        from ..components import Transform

        # Optimization: Quadtree or spatial hash would be better, but O(N^2) for small N is fine
        entities = world.get_entities_with(RelationshipRegistry, YukkuriStats, Transform)

        for i, eid in enumerate(entities):
            reg = world.get_component(eid, RelationshipRegistry)
            if reg.family_group_id is None:
                continue

            stats = world.get_component(eid, YukkuriStats)
            trans = world.get_component(eid, Transform)

            for j in range(i + 1, len(entities)):
                other_eid = entities[j]
                other_reg = world.get_component(other_eid, RelationshipRegistry)

                if other_reg.family_group_id == reg.family_group_id:
                    # Same family
                    other_trans = world.get_component(other_eid, Transform)

                    dist_sq = (trans.x - other_trans.x)**2 + (trans.y - other_trans.y)**2
                    if dist_sq < 100 * 100: # 100 pixels
                        # Taking it easy together
                        stats.happiness = min(100.0, stats.happiness + 0.1)
                        stats.stress = max(0.0, stats.stress - 0.1)

                        other_stats = world.get_component(other_eid, YukkuriStats)
                        other_stats.happiness = min(100.0, other_stats.happiness + 0.1)
                        other_stats.stress = max(0.0, other_stats.stress - 0.1)
