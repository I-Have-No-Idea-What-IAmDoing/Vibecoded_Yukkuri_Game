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
    System responsible for Poop mechanics:
    1. Spawning poop periodically or based on cleanliness.
    2. Reducing cleanliness of Yukkuris near poop.

    Attributes:
        spawn_chance_per_second (float): Probability of pooping per second.
        poop_radius (float): Radius within which poop affects cleanliness.
        smell_strength (float): Amount of cleanliness lost per second near poop.
    """

    def __init__(self) -> None:
        """Initializes the PoopSystem with default configuration."""
        # Configuration
        super().__init__()
        self.spawn_chance_per_second = 0.01  # % chance per second to poop randomly
        self.poop_radius = 200.0
        self.smell_strength = 5.0  # Cleanliness lost per second when near poop

    def update(self, world: World, dt: float) -> None:
        """
        Updates the PoopSystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        # 1. Spawning Poop
        # Iterate over Yukkuris
        for entity, (stats, needs, transform, ai) in world.get_components_tuple(
            YukkuriStats, Needs, Transform, AIState
        ):
            should_poop = False

            # Periodic/Random spawning logic
            if rng.random_float() < self.spawn_chance_per_second * dt:
                should_poop = True

            # Bladder Logic
            # If bladder is full, they must poop (or pee? Poop component handles "waste")
            if needs.bladder > 80.0:
                if rng.random_float() < 0.1 * dt:  # High chance when full
                    should_poop = True

            # Or if cleanliness is very low (lose control)
            if needs.cleanliness < 10.0:
                if rng.random_float() < (self.spawn_chance_per_second * 5) * dt:
                    should_poop = True

            if should_poop:
                offset_x = rng.uniform(-10, 10)
                offset_y = rng.uniform(-10, 10)
                create_poop(world, transform.x + offset_x, transform.y + offset_y)

                needs.cleanliness = max(0, needs.cleanliness - 5)
                needs.bladder = 0.0

        # 2. Environmental Effect
        # Find all poop entities
        poop_entities = world.get_entities_with(Poop, Transform)
        if not poop_entities:
            return

        # Optimization: In a large game, use a spatial grid. Here, O(N*M) is fine for small counts.
        for p_ent in poop_entities:
            p_trans = world.get_component(p_ent, Transform)
            if p_trans is None:
                continue

            for y_ent, (y_stats, y_needs, y_trans) in world.get_components_tuple(
                YukkuriStats, Needs, Transform
            ):
                # Distance check
                dist_sq = (p_trans.x - y_trans.x) ** 2 + (p_trans.y - y_trans.y) ** 2

                if dist_sq < self.poop_radius**2:
                    # Constant decay if within radius
                    y_needs.cleanliness -= self.smell_strength * dt
                    y_needs.cleanliness = max(0, y_needs.cleanliness)
