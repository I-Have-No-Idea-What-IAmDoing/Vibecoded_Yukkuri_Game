import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.game.yukkuri_components import (
    AIState,
    Blackboard,
    YukkuriStats,
    Predator,
    RelationshipRegistry,
)
from yukkuri_game.game.components import Transform
from yukkuri_game.engine.ecs import World


class TestPerceptionSystem:
    @pytest.fixture
    def world(self):
        return MagicMock(spec=World)

    @pytest.fixture
    def system(self):
        return PerceptionSystem()

    def test_update_blackboard_basic(self, world, system):
        """Test basic visibility translation to Blackboard."""
        entity_id = 1
        target_id = 2

        # Setup Entity 1 (Observer)
        ai_state = AIState(visible_entities={target_id})
        blackboard = Blackboard()
        trans = Transform(x=0, y=0)

        # Setup components retrieval for Observer
        world.try_get_component.side_effect = lambda e, c: None

        # Setup Target Entity 2
        target_trans = Transform(x=10, y=0)

        def try_get_component_mock(e, c):
            if e == target_id and c == Transform:
                return target_trans
            if e == entity_id and c == YukkuriStats:
                return None
            return None

        world.try_get_component.side_effect = try_get_component_mock

        # Run update logic manually
        system._update_blackboard(
            world, entity_id, ai_state, blackboard, trans, current_time=100.0
        )

        assert target_id in blackboard.visible_targets
        target_info = blackboard.visible_targets[target_id]
        assert target_info.distance == 10.0
        assert target_info.relation == "Neutral"
        assert target_info.timestamp == 100.0

    def test_social_context_predator_prey(self, world, system):
        """Test Predator seeing Prey."""
        entity_id = 1
        target_id = 2

        ai_state = AIState(visible_entities={target_id})
        blackboard = Blackboard()
        trans = Transform(x=0, y=0)

        # Observer is Predator
        my_predator = Predator(prey_tags={"FoodType"})

        # Target is Prey
        target_stats = YukkuriStats(name="Target", type_id="FoodType")
        target_trans = Transform(x=10, y=0)

        def try_get_component_mock(e, c):
            if e == entity_id:
                if c == Predator:
                    return my_predator
                if c == YukkuriStats:
                    return None
            if e == target_id:
                if c == Transform:
                    return target_trans
                if c == YukkuriStats:
                    return target_stats
            return None

        world.try_get_component.side_effect = try_get_component_mock

        # Mocking world.get_components_tuple is not needed for _update_blackboard
        # But we need to mock world.try_get_component calls inside the system Update

        # Actually, let's inject components directly via the mocked world if we could,
        # but since we're calling _update_blackboard directly, we just need to ensure
        # world.try_get_component returns the right things.

        # Re-rig the mock for this specific test case flow
        def robust_get_component(e, c):
            if e == entity_id:
                if c == Predator:
                    return my_predator
                if c == YukkuriStats:
                    return None
                if c == RelationshipRegistry:
                    return None
            if e == target_id:
                if c == Transform:
                    return target_trans
                if c == YukkuriStats:
                    return target_stats
                if c == Predator:
                    return None
            return None

        world.try_get_component.side_effect = robust_get_component

        system._update_blackboard(
            world, entity_id, ai_state, blackboard, trans, current_time=100.0
        )

        assert blackboard.visible_targets[target_id].relation == "Prey"
        assert blackboard.closest_food_id == target_id

    def test_memory_persistence(self, world, system):
        """Test short-term memory of lost targets."""
        entity_id = 1
        target_id = 2

        ai_state = AIState(visible_entities={target_id})
        blackboard = Blackboard()
        trans = Transform(x=0, y=0)
        target_trans = Transform(x=10, y=0)

        # 1. First update: Target is visible
        world.try_get_component.side_effect = (
            lambda e, c: target_trans if (e == target_id and c == Transform) else None
        )

        system._update_blackboard(
            world, entity_id, ai_state, blackboard, trans, current_time=100.0
        )
        assert target_id in blackboard.visible_targets

        # 2. Second update: Target lost (removed from visible_entities)
        ai_state.visible_entities = set()

        system._update_blackboard(
            world, entity_id, ai_state, blackboard, trans, current_time=101.0
        )

        assert target_id not in blackboard.visible_targets
        assert target_id in blackboard.short_term_memory
        assert blackboard.short_term_memory[target_id].position == (10, 0)

        # 3. Third update: Memory expires
        # MEMORY_DURATION is 10.0, so we need > 10s elapsed
        system._update_blackboard(
            world, entity_id, ai_state, blackboard, trans, current_time=120.0
        )

        assert target_id not in blackboard.short_term_memory
