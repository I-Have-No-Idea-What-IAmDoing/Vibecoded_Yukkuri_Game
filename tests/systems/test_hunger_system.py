"""
Unit tests for the HungerSystem.
"""

import pytest
from unittest.mock import MagicMock

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.systems.hunger_system import HungerSystem
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.components import (
    YukkuriStats,
    Needs,
    ItemStats,
    AIState,
    EmotionalState,
)
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.game.skill_constants import SkillId


class TestHungerSystemInitialization:
    """Tests for HungerSystem initialization."""

    def test_initialization(self) -> None:
        """HungerSystem initializes with None services."""
        system = HungerSystem()
        assert system.audio is None
        assert system.skill_service is None

    def test_update_loads_services(self) -> None:
        """update() loads services from world."""
        from test_utils import make_configured_world
        world = make_configured_world()
        audio = MagicMock(spec=AudioManager)
        skill_service = MagicMock(spec=SkillService)
        
        # Register mocks (overwriting defaults from make_configured_world if any)
        world.services.register(audio, AudioManager, replace=True)
        world.services.register(skill_service, SkillService, replace=True)

        system = HungerSystem()
        system.update(world, 0.016)

        assert system.audio == audio
        assert system.skill_service == skill_service


class TestProcessConsumption:
    """Tests for process_consumption method."""

    @pytest.fixture
    def setup_world(self):
        """Create a world with consumer and item entities."""
        from test_utils import make_configured_world
        world = make_configured_world()

        # Consumer entity
        consumer_id = world.create_entity()
        consumer_stats = YukkuriStats(name="Test", type_id="reimu")
        consumer_transform = Transform(x=100, y=100)
        consumer_needs = Needs(hunger=50, energy=50, bladder=20)
        consumer_emotional = EmotionalState(happiness=50)
        consumer_ai = AIState()

        world.add_component(consumer_id, consumer_stats)
        world.add_component(consumer_id, consumer_transform)
        world.add_component(consumer_id, consumer_needs)
        world.add_component(consumer_id, consumer_emotional)
        world.add_component(consumer_id, consumer_ai)

        # Item entity
        item_id = world.create_entity()
        item_stats = ItemStats(
            name="Test Food",
            type_id="food",
            cost=10,
            nutrition=30,
            fun=10,
            comfort=5,
        )
        item_transform = Transform(x=110, y=110)  # Close to consumer

        world.add_component(item_id, item_stats)
        world.add_component(item_id, item_transform)

        return {
            "world": world,
            "consumer_id": consumer_id,
            "item_id": item_id,
            "consumer_stats": consumer_stats,
            "consumer_transform": consumer_transform,
            "consumer_needs": consumer_needs,
            "consumer_emotional": consumer_emotional,
            "item_stats": item_stats,
        }

    def test_consumption_reduces_hunger(self, setup_world):
        """Eating item reduces hunger."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        result = system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert result is True
        # hunger was 50, nutrition is 30, so new hunger = 50 - 30 = 20
        assert data["consumer_needs"].hunger == 20

    def test_consumption_increases_bladder(self, setup_world):
        """Eating item increases bladder."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        # bladder was 20, nutrition is 30, waste = 30 * 0.5 = 15
        # new bladder = 20 + 15 = 35
        assert data["consumer_needs"].bladder == 35

    def test_consumption_increases_happiness(self, setup_world):
        """Eating fun item increases happiness."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        # happiness was 50, fun is 10, new happiness = 60
        assert data["consumer_emotional"].happiness == 60

    def test_consumption_increases_energy(self, setup_world):
        """Eating comfortable item increases energy."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        # energy was 50, comfort is 5, new energy = 55
        assert data["consumer_needs"].energy == 55

    def test_consumption_fails_if_too_far(self, setup_world):
        """Consumption fails if item is too far away."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        # Move item far away
        item_transform = world.get_component(data["item_id"], Transform)
        item_transform.x = 500
        item_transform.y = 500

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        result = system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert result is False
        # Hunger should not change
        assert data["consumer_needs"].hunger == 50

    def test_consumption_destroys_item_when_consume_true(self, setup_world):
        """Item is destroyed when consume=True."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        # Entity should be marked destroyed
        assert not world.entity_exists(data["item_id"])

    def test_play_does_not_consume_or_feed(self, setup_world):
        """Playing (consume=False) increases happiness but ignores nutrition and destruction."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        request = InteractionRequest(target_id=data["item_id"], consume=False)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        # Assert Happiness Increased (fun is 10, start is 50 -> 60)
        assert data["consumer_emotional"].happiness == 60

        # Assert Hunger Unchanged (Nutrition ignored)
        assert data["consumer_needs"].hunger == 50
        assert data["consumer_needs"].bladder == 20

        # Assert Item Still Exists
        assert world.entity_exists(data["item_id"])

    def test_consumption_plays_sound(self, setup_world):
        """Eating plays 'eat' sound."""
        data = setup_world
        world = data["world"]

        audio = MagicMock(spec=AudioManager)
        world.services.register(audio, AudioManager)

        system = HungerSystem()
        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        audio.play_sound.assert_called_with("eat")

    def test_consumption_adds_scavenging_xp(self, setup_world):
        """Eating grants scavenging XP."""
        data = setup_world
        world = data["world"]

        skill_service = MagicMock(spec=SkillService)
        world.services.register(skill_service, SkillService)

        system = HungerSystem()
        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        skill_service.add_xp.assert_called_with(
            data["consumer_id"], SkillId.SCAVENGING, 5.0
        )

    def test_consumption_clears_ai_target(self, setup_world):
        """Eating clears AI target if it was the item."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        ai = world.get_component(data["consumer_id"], AIState)
        ai.current_target_id = data["item_id"]

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert ai.current_target_id == -1

    def test_consumption_fails_without_needs(self, setup_world):
        """Consumption fails if consumer has no Needs component."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        # Remove needs component
        world.remove_component(data["consumer_id"], Needs)

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        result = system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert result is False

    def test_consumption_fails_without_item_transform(self, setup_world):
        """Consumption fails if item has no Transform."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        # Remove item transform
        world.remove_component(data["item_id"], Transform)

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        result = system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert result is False

    def test_hunger_clamped_to_zero(self, setup_world):
        """Hunger cannot go below 0."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        # Set hunger low
        data["consumer_needs"].hunger = 10

        # Item with high nutrition
        data["item_stats"].nutrition = 50

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert data["consumer_needs"].hunger == 0

    def test_bladder_clamped_to_max(self, setup_world):
        """Bladder cannot exceed 100."""
        data = setup_world
        world = data["world"]
        system = HungerSystem()

        # Set bladder high
        data["consumer_needs"].bladder = 95

        # Item with nutrition that would push over
        data["item_stats"].nutrition = 20  # waste = 10

        request = InteractionRequest(target_id=data["item_id"], consume=True)

        system.process_consumption(
            world,
            data["consumer_id"],
            request,
            data["consumer_transform"],
            data["item_id"],
            data["item_stats"],
        )

        assert data["consumer_needs"].bladder == 100
