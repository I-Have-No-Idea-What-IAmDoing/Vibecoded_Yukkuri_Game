import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.yukkuri_components import Personality, RelationshipRegistry, RelationshipData, YukkuriStats
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.services import TimeService
from yukkuri_game.game.events import SocialInteractionEvent

class TestSocialSystem:
    @pytest.fixture
    def event_bus(self):
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def world(self, event_bus):
        world = MagicMock(spec=World)
        world.get_entities_with.return_value = []

        # Services
        services = MagicMock()
        world.services = services

        return world

    @pytest.fixture
    def system(self, event_bus, world):
        sys = SocialSystem(event_bus)
        sys.ecs_world = world
        return sys

    def test_mood_decay(self, system, world):
        e1 = 1
        pers = Personality(mood_score=50.0)
        stats = YukkuriStats(name="test", type_id="test")

        # Setup world mocks
        def get_entities_with_side_effect(t):
            if t == Personality:
                return [e1]
            return []

        world.get_entities_with.side_effect = get_entities_with_side_effect
        world.get_component.side_effect = lambda e, t: pers if t == Personality else None

        # Mock get_components_tuple which is used by the system
        world.get_components_tuple.return_value = [(e1, (pers, stats))]

        system.update(world, 1.0)

        # Decay rate is 5.0 per sec
        assert pers.mood_score == 45.0

        # Test min cap
        pers.mood_score = 2.0
        system.update(world, 1.0)
        assert pers.mood_score == 0.0
        assert pers.mood == "NEUTRAL"

    def test_cleanup_relationships(self, system, world):
        import time

        e1 = 1
        reg = RelationshipRegistry()
        # Old relationship: updated 10 minutes (600s) + 100s ago
        # We use a mock time base to ensure consistency
        base_time = 10000.0

        reg.relationships[2] = RelationshipData(last_update=base_time - 700)
        # Active relationship
        reg.relationships[3] = RelationshipData(last_update=base_time)

        # Mock behavior to return correct components
        def get_entities_with_side_effect(t):
             if t == RelationshipRegistry:
                 return [e1]
             if t == Personality:
                 return []
             return []

        world.get_entities_with.side_effect = get_entities_with_side_effect

        def get_component_side_effect(e, t):
             if t == RelationshipRegistry:
                 return reg
             return None

        world.get_component.side_effect = get_component_side_effect
        # Mock has_component to return false for "is_special" check (not mate/family)
        world.has_component.return_value = False

        # Mock TimeService
        time_service = MagicMock(spec=TimeService)
        time_service.time_elapsed = base_time

        def try_get_side_effect(service_type):
            if service_type == TimeService:
                return time_service
            return None

        world.services.try_get.side_effect = try_get_side_effect

        system.update(world, 0.1)

        # Relationship 2 should be removed because 700 > 600 (cutoff)
        assert 2 not in reg.relationships
        # Relationship 3 should remain
        assert 3 in reg.relationships

    def test_social_interaction_event(self, system, world):
        # Setup trait service
        trait_service = MagicMock(spec=TraitService)
        time_service = MagicMock(spec=TimeService)
        time_service.time_elapsed = 1000.0

        def try_get_side_effect(service_type):
            if service_type == TraitService:
                return trait_service
            if service_type == TimeService:
                return time_service
            return None

        world.services.try_get.side_effect = try_get_side_effect

        interaction_data = {
            "base_impact": 10.0,
            "social_impact": {"affinity": 5.0, "trust": 2.0}
        }
        trait_service.get_interaction.return_value = interaction_data

        # Entities
        actor_id = 1
        target_id = 2

        # Components
        reg_target = RelationshipRegistry()
        pers_target = Personality()

        def get_component(e, c):
            if e == target_id:
                if c == RelationshipRegistry: return reg_target
                if c == Personality: return pers_target
            return None

        world.get_component.side_effect = get_component
        # Mock entity_exists
        world.entity_exists.return_value = True

        # Trigger event handler directly
        event = SocialInteractionEvent(actor_id, target_id, "Greet")
        system.on_social_interaction(event)

        # Check effects on target regarding actor
        assert actor_id in reg_target.relationships
        rel = reg_target.relationships[actor_id]

        assert rel.affinity == 5.0
        assert rel.trust == 2.0
        assert len(rel.memories) == 1

    def test_apply_impact_mood_change(self, system, world):
        trait_service = MagicMock(spec=TraitService)
        world.services.try_get.return_value = trait_service

        # Strong positive impact
        interaction_data = {"base_impact": 20.0}
        trait_service.get_interaction.return_value = interaction_data

        e1 = 1
        pers = Personality()
        reg = RelationshipRegistry()

        def get_component(e, c):
            if c == Personality: return pers
            if c == RelationshipRegistry: return reg
            return None
        world.get_component.side_effect = get_component

        system._apply_impact(world, e1, 2, interaction_data, "target", now=1000.0)

        assert pers.mood == "HAPPY"
        assert pers.mood_score == 100.0

    def test_relationship_decay_logic(self, system):
        rel_data = RelationshipData(affinity=50.0, fear=10.0, trust=60.0, last_update=0.0)

        import time
        now = time.time()

        # First update just sets timestamp
        system._update_relationship_decay(rel_data, now)
        assert rel_data.last_update == now

        # Advance time to simulate elapsed time
        now += 100.0

        system._update_relationship_decay(rel_data, now)

        # Affinity decay: 0.01 * 100 = 1.0
        assert rel_data.affinity < 50.0
        # Fear decay: 0.05 * 100 = 5.0
        assert rel_data.fear < 10.0
        # Trust decay: 0.005 * 100 = 0.5
        assert rel_data.trust < 60.0
