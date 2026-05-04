import pytest
from test_utils import make_configured_world
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.yukkuri_components import (
    Personality,
    RelationshipRegistry,
    RelationshipData,
    EmotionalState,
)
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
        sys = SocialSystem()
        sys.ecs_world = world
        return sys

    def test_cleanup_relationships(self, system, world):
        e1 = 1
        reg = RelationshipRegistry()
        # Old relationship: updated 10 minutes (600s) + 100s ago
        # We use a mock time base to ensure consistency
        base_time = 10000.0

        reg.relationships[2] = RelationshipData(last_update=base_time - 700)
        # Active relationship
        reg.relationships[3] = RelationshipData(last_update=base_time)

        # Mock behavior to return correct components
        def get_components_tuple_side_effect(*args):
            if args[0] == RelationshipRegistry:
                return [(e1, (reg,))]
            return []

        world.get_components_tuple.side_effect = get_components_tuple_side_effect

        def get_component_side_effect(e, t):
            if t == RelationshipRegistry:
                return reg
            if t == Personality:
                return Personality()  # Return empty personality for drift calculation
            return None

        world.get_component.side_effect = get_component_side_effect
        # Mock has_component to return false for "is_special" check (not mate/family)
        world.has_component.return_value = False

        # Mock TimeService
        time_service = MagicMock(spec=TimeService)
        time_service.time_elapsed = base_time
        # IMPORTANT: Set world.time to float, as MagicMock won't use the property getter
        world.time = base_time

        trait_service = MagicMock(spec=TraitService)

        def try_get_side_effect(service_type):
            if service_type == TimeService:
                return time_service
            if service_type == TraitService:
                return trait_service
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
        world.time = 1000.0  # Fix: Ensure world.time is float

        # Mock Config for Memory Threshold
        config = MagicMock()
        config.rules.social.memory_importance_threshold = 50.0

        def try_get_side_effect(service_type):
            if service_type == TraitService:
                return trait_service
            if service_type == TimeService:
                return time_service
            if "GameConfig" in str(
                service_type
            ):  # Checking class name approximately or import
                return config
            return None

        world.services.try_get.side_effect = try_get_side_effect

        interaction_data = {
            "base_impact": 10.0,
            "social_impact": {"affinity": 5.0, "trust": 2.0},
        }
        trait_service.get_interaction.return_value = interaction_data

        # Entities
        actor_id = 1
        target_id = 2

        # Components
        reg_target = RelationshipRegistry()
        pers_target = Personality()
        emotional = EmotionalState()

        def get_component(e, c):
            if e == target_id:
                if c == RelationshipRegistry:
                    return reg_target
                if c == Personality:
                    return pers_target
                if c == EmotionalState:
                    return emotional
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

        # Since Opinion is recalculated, and memory sentiment is 5.0, affinity should be around 5.0
        # Base compatibility is 0 (default personalities).
        # Actually default personality axis are 0,0,0,0 so diff is 0.
        # Base compatibility = 100.0 (from 100 - 0/4)
        # Wait, if base is 100, affinity will be 100 + 5.0 = 105 -> clamped to 100.

        # Let's verify memories
        assert len(rel.trivial_buffer) == 1
        assert rel.trivial_buffer[0].sentiment == 5.0

    def test_apply_impact_emotional_change(self, system, world):
        trait_service = MagicMock(spec=TraitService)
        config = MagicMock()
        config.rules.social.memory_importance_threshold = (
            50.0  # Fix: Set value for threshold comparison
        )

        world.services.try_get.side_effect = (
            lambda s: trait_service
            if s == TraitService
            else (config if "GameConfig" in str(s) else None)
        )

        # Strong positive impact
        interaction_data = {"base_impact": 20.0}
        trait_service.get_interaction.return_value = interaction_data

        e1 = 1
        pers = Personality()
        reg = RelationshipRegistry()
        emotional = EmotionalState()

        def get_component(e, c):
            if c == Personality:
                return pers
            if c == RelationshipRegistry:
                return reg
            if c == EmotionalState:
                return emotional
            return None

        world.get_component.side_effect = get_component

        system._apply_impact(world, e1, 2, interaction_data, "target", now=1000.0)

        # Base impact > 15 -> Happiness + 20
        assert emotional.happiness == 20.0
