import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.game.components import (
    AIState,
    Blackboard,
    YukkuriStats,
    Predator,
    RelationshipRegistry,
    ItemStats,
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

        # Setup maps
        stats_map = {}
        predator_map = {}
        relationship_map = {}
        item_map = {}

        # Setup Target Entity 2
        target_trans = Transform(x=10, y=0)
        transform_map = {target_id: target_trans}

        # Run update logic manually
        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=100.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
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

        # Maps
        stats_map = {target_id: target_stats}
        predator_map = {entity_id: my_predator}
        relationship_map = {}
        item_map = {}
        transform_map = {target_id: target_trans}

        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=100.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
        )
        
        # Advance time to bypass reaction delay (0.5s default)
        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=101.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
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

        stats_map = {}
        predator_map = {}
        relationship_map = {}
        item_map = {}
        transform_map = {target_id: target_trans}

        # 1. First update: Target is visible
        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=100.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
        )
        assert target_id in blackboard.visible_targets

        # 2. Second update: Target lost (removed from visible_entities)
        ai_state.visible_entities = set()

        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=101.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
        )

        assert target_id not in blackboard.visible_targets
        assert target_id in blackboard.short_term_memory
        assert blackboard.short_term_memory[target_id].position == (10, 0)

        # 3. Third update: Memory expires
        # MEMORY_DURATION is 10.0, so we need > 10s elapsed
        system._update_blackboard(
            world,
            entity_id,
            ai_state,
            blackboard,
            trans,
            current_time=120.0,
            stats_map=stats_map,
            predator_map=predator_map,
            relationship_map=relationship_map,
            item_map=item_map,
            transform_map=transform_map
        )

        assert target_id not in blackboard.short_term_memory
