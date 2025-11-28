"""
Module defining the PoopSystem logic.
"""
import random
import math
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Poop, AIState
from ..components import Transform

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
        self.spawn_chance_per_second = 0.01 # % chance per second to poop randomly
        self.poop_radius = 200.0
        self.smell_strength = 5.0 # Cleanliness lost per second when near poop

    def update(self, world: World, dt: float) -> None:
        """
        Updates the PoopSystem.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        from ..entity_factory import EntityFactory
        factory = world.services.try_get(EntityFactory)

        # 1. Spawning Poop
        # Iterate over Yukkuris
        for entity, (stats, transform, ai) in world.get_components_tuple(YukkuriStats, Transform, AIState):
            should_poop = False

            # Periodic/Random spawning logic
            # We could use a timer in AIState or just random chance.
            # Let's use a simple random chance for now.
            if random.random() < self.spawn_chance_per_second * dt:
                should_poop = True

            # Or if cleanliness is very low (lose control)
            # Note: Task said "Spawn ... when cleanliness drops below threshold".
            # This implies low cleanliness -> poop.
            if stats.cleanliness < 10.0:
                 if random.random() < (self.spawn_chance_per_second * 5) * dt:
                     should_poop = True

            if should_poop and factory:
                # Spawn behind them? or just at position.
                # Add a small offset so they don't get stuck inside it immediately if using physics
                offset_x = random.uniform(-10, 10)
                offset_y = random.uniform(-10, 10)
                factory.create_poop(transform.x + offset_x, transform.y + offset_y)

                # Feedback: Pooping might raise cleanliness slightly (relief) or lower it (dirty)?
                # Task says "Poop entities lower cleanliness", implying environmental.
                # Usually pooping itself might lower internal cleanliness?
                # Let's say they get a bit dirtier by pooping.
                stats.cleanliness = max(0, stats.cleanliness - 5)

                # Play sound? (Access AudioManager if needed)

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

            for y_ent, (y_stats, y_trans) in world.get_components_tuple(YukkuriStats, Transform):
                # Distance check
                dist_sq = (p_trans.x - y_trans.x)**2 + (p_trans.y - y_trans.y)**2

                if dist_sq < self.poop_radius**2:
                    # Calculate falloff? Or constant?
                    # Constant decay if within radius
                    y_stats.cleanliness -= self.smell_strength * dt
                    y_stats.cleanliness = max(0, y_stats.cleanliness)
