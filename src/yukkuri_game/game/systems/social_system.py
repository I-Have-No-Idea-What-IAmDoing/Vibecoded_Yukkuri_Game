import random
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Personality, SocialMemory

class SocialSystem(System):
    """
    System responsible for social dynamics, including mood updates and relationship decay.
    """

    def update(self, world: World, dt: float) -> None:
        self._update_moods(world)
        self._decay_relationships(world, dt)

    def _update_moods(self, world: World) -> None:
        # Get all entities with Stats and Personality
        entities = world.get_components_tuple(YukkuriStats, Personality)

        for entity, (stats, personality) in entities:
            # Simple mood logic based on stats
            if stats.health < 30.0 or stats.stress > 80.0:
                if stats.health < 30.0 and stats.stress > 80.0:
                    personality.mood = "Scared"
                elif stats.hunger > 80.0:
                     personality.mood = "Angry"
                else:
                    personality.mood = "Stressed"
            elif stats.happiness < 20.0:
                personality.mood = "Depressed"
            elif stats.happiness > 80.0 and stats.stress < 20.0:
                personality.mood = "Happy"
            else:
                personality.mood = "Neutral"

    def _decay_relationships(self, world: World, dt: float) -> None:
        # Get all entities with SocialMemory
        entities = world.get_components_tuple(SocialMemory)

        decay_rate = 0.5 * dt # Points per second decay towards neutral

        for entity, (memory,) in entities:
            to_remove = []
            for target_id, rel in memory.relationships.items():
                # Decay Affection towards 0
                if rel.affection > 0:
                    rel.affection = max(0.0, rel.affection - decay_rate)
                elif rel.affection < 0:
                    rel.affection = min(0.0, rel.affection + decay_rate)

                # Decay Trust towards 0 (slower)
                if rel.trust > 0:
                    rel.trust = max(0.0, rel.trust - (decay_rate * 0.5))
                elif rel.trust < 0:
                    rel.trust = min(0.0, rel.trust + (decay_rate * 0.5))

                # Dominance tends to stick longer, maybe decay very slowly
                # For now, let's leave dominance stable

                # If relationship is effectively neutral and target doesn't exist, remove it
                if (abs(rel.affection) < 1.0 and
                    abs(rel.trust) < 1.0 and
                    abs(rel.dominance) < 1.0):
                    if not world.entity_exists(target_id):
                        to_remove.append(target_id)

            for target_id in to_remove:
                del memory.relationships[target_id]
