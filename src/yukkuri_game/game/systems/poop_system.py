"""
Module defining the PoopSystem logic.
"""

from ...engine import rng
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Needs, Poop, AIState
from ..components import Transform
from ..prefabs.item import create_poop


class PoopSystem(System):
    """
    System responsible for Poop mechanics.

    Mechanics:
    1.  Spawning poop periodically or based on cleanliness/bladder.
    2.  Reducing cleanliness of Yukkuris near poop.

    Attributes:
        spawn_chance_per_second (float): Probability of pooping per second.
        poop_radius (float): Radius within which poop affects cleanliness.
        smell_strength (float): Amount of cleanliness lost per second near poop.
    """

    # Spawning probabilities
    BASE_SPAWN_CHANCE = 0.01  # % chance per second to poop randomly
    BLADDER_FULL_THRESHOLD = 80.0  # Must poop above this
    BLADDER_FULL_CHANCE_MULT = 10.0  # (0.1 / 0.01) = 10x chance when full
    CLEANLINESS_CRITICAL_THRESHOLD = 10.0  # Lose control below this
    CLEANLINESS_CRITICAL_CHANCE_MULT = 5.0  # 5x chance when filthy

    # Consequences
    SPAWN_CLEANLINESS_PENALTY = 5.0  # Cleanliness lost upon pooping
    SPAWN_OFFSET_RANGE = 10.0  # Random positioning jitter

    # Environmental effect
    DEFAULT_SMELL_RADIUS = 200.0
    DEFAULT_SMELL_STRENGTH = 5.0

    def __init__(self) -> None:
        """Initializes the PoopSystem with default configuration."""
        super().__init__()
        self.spawn_chance_per_second = self.BASE_SPAWN_CHANCE
        self.poop_radius = self.DEFAULT_SMELL_RADIUS
        self.smell_strength = self.DEFAULT_SMELL_STRENGTH

    def update(self, world: World, dt: float) -> None:
        """
        Updates the PoopSystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Spawning Poop
        # Iterate over Yukkuris
        for entity, (stats, needs, transform, ai) in world.get_components_tuple(
            YukkuriStats, Needs, Transform, AIState
        ):
            should_poop = False

            # Periodic/Random spawning logic
            if rng.random_float() < self.spawn_chance_per_second * dt:
                should_poop = True

            # Bladder Logic
            # If bladder is full, they must poop
            if needs.bladder > self.BLADDER_FULL_THRESHOLD:
                if (
                    rng.random_float()
                    < (self.spawn_chance_per_second * self.BLADDER_FULL_CHANCE_MULT)
                    * dt
                ):
                    should_poop = True

            # Cleanliness low (lose control)
            if needs.cleanliness < self.CLEANLINESS_CRITICAL_THRESHOLD:
                if (
                    rng.random_float()
                    < (
                        self.spawn_chance_per_second
                        * self.CLEANLINESS_CRITICAL_CHANCE_MULT
                    )
                    * dt
                ):
                    should_poop = True

            if should_poop:
                offset_x = rng.uniform(
                    -self.SPAWN_OFFSET_RANGE, self.SPAWN_OFFSET_RANGE
                )
                offset_y = rng.uniform(
                    -self.SPAWN_OFFSET_RANGE, self.SPAWN_OFFSET_RANGE
                )
                create_poop(world, transform.x + offset_x, transform.y + offset_y)

                needs.cleanliness = max(
                    0.0, needs.cleanliness - self.SPAWN_CLEANLINESS_PENALTY
                )
                needs.bladder = 0.0

        # Environmental Effect
        # Find all poop entities
        poop_entities = world.get_components_tuple(Poop, Transform)
        if not poop_entities:
            return

        from .spatial_system import SpatialService
        spatial_service = world.services.try_get(SpatialService)

        poop_radius = self.poop_radius
        poop_radius_sq = poop_radius ** 2
        smell_strength_dt = self.smell_strength * dt

        if spatial_service:
            # Pre-fetch component maps for O(1) lookups
            yukkuri_needs_map = world.get_components(Needs)
            trans_map = world.get_components(Transform)
            yukkuri_stats_map = world.get_components(YukkuriStats)

            for _p_ent, (_p_poop, p_trans) in poop_entities:
                px, py = p_trans.x, p_trans.y
                nearby_entities = spatial_service.get_entities_in_radius(px, py, poop_radius)

                for _y_ent in nearby_entities:
                    if _y_ent not in yukkuri_stats_map or _y_ent not in yukkuri_needs_map or _y_ent not in trans_map:
                        continue

                    y_trans = trans_map[_y_ent]

                    dist_sq = (px - y_trans.x) ** 2 + (py - y_trans.y) ** 2
                    if dist_sq < poop_radius_sq:
                        y_needs = yukkuri_needs_map[_y_ent]
                        y_needs.cleanliness = max(0.0, y_needs.cleanliness - smell_strength_dt)
        else:
            # Fallback for when SpatialService is not available (e.g. tests)
            for _p_ent, (_p_poop, p_trans) in poop_entities:
                for _y_ent, (_y_stats, y_needs, y_trans) in world.get_components_tuple(
                    YukkuriStats, Needs, Transform
                ):
                    # Distance check
                    dist_sq = (p_trans.x - y_trans.x) ** 2 + (p_trans.y - y_trans.y) ** 2

                    if dist_sq < poop_radius_sq:
                        # Constant decay if within radius
                        y_needs.cleanliness -= smell_strength_dt
                        y_needs.cleanliness = max(0.0, y_needs.cleanliness)
