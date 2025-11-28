import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.services import (
    TimeService, EconomyService, InputService, PersistenceService, GameService
)
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, AIState

class TestTimeService:
    def test_time_elapsed(self):
        service = TimeService()
        assert service.time_elapsed == 0.0

        service.add_time(1.5)
        assert service.time_elapsed == 1.5

        service.time_elapsed = 10.0
        assert service.time_elapsed == 10.0

class TestEconomyService:
    def test_initial_money(self):
        service = EconomyService(initial_money=500)
        assert service.get_money() == 500

    def test_add_money(self):
        service = EconomyService(100)
        service.add_money(50)
        assert service.get_money() == 150

        with pytest.raises(ValueError):
            service.add_money(-10)

    def test_remove_money(self):
        service = EconomyService(100)
        assert service.remove_money(50) is True
        assert service.get_money() == 50

        assert service.remove_money(60) is False
        assert service.get_money() == 50

        with pytest.raises(ValueError):
            service.remove_money(-10)

    def test_set_money(self):
        service = EconomyService(100)
        service.set_money(200)
        assert service.get_money() == 200

        service.set_money(-50)
        assert service.get_money() == 0

class TestInputService:
    def test_placement_mode(self):
        service = InputService()
        assert service.is_placing is False

        service.start_placement("test_item", 100, "item")
        assert service.is_placing is True
        assert service.place_type == "test_item"
        assert service.place_cost == 100
        assert service.place_entity_type == "item"
        assert service.is_cleaning is False

        service.cancel_placement()
        assert service.is_placing is False
        assert service.place_type == ""

    def test_cleaning_mode(self):
        service = InputService()
        service.start_cleaning()
        assert service.is_cleaning is True
        assert service.is_placing is False

        service.stop_cleaning()
        assert service.is_cleaning is False

    def test_cleaning_interrupts_placement(self):
        service = InputService()
        service.start_placement("t", 10, "i")
        service.start_cleaning()
        assert service.is_cleaning is True
        assert service.is_placing is False

class TestPersistenceService:
    @pytest.fixture
    def mock_world(self):
        return MagicMock(spec=World)

    @pytest.fixture
    def mock_os(self):
        with patch('yukkuri_game.game.services.os') as mock:
            mock.path.join.side_effect = lambda a, b: f"{a}/{b}"
            mock.path.exists.return_value = True
            yield mock

    @pytest.fixture
    def mock_json(self):
        with patch('yukkuri_game.game.services.json') as mock:
            yield mock

    @pytest.fixture
    def mock_open(self):
        with patch('builtins.open', new_callable=MagicMock) as mock:
             yield mock

    def test_save_game(self, mock_world, mock_os, mock_json, mock_open):
        service = PersistenceService(mock_world)

        # Mock EconomyService
        mock_economy = MagicMock(spec=EconomyService)
        mock_economy.get_money.return_value = 500
        # Mock world.services
        mock_world.services = MagicMock()
        mock_world.services.try_get.side_effect = lambda t: mock_economy if t == EconomyService else None

        # Mock Entities
        mock_world.get_all_entities.return_value = [1]
        mock_world.has_component.side_effect = lambda e, c: True

        mock_trans = MagicMock(x=10, y=20)
        mock_stats = MagicMock(type_id="reimu", health=100, hunger=50, happiness=80, badges=0, age=1)
        mock_stats.name = "Reimu"
        mock_ai = MagicMock(current_action="Idle", current_target_id=-1, action_progress=0, state_data={}, path=[])

        def get_component_side_effect(e, c):
            if c == Transform: return mock_trans
            if c == YukkuriStats: return mock_stats
            if c == AIState: return mock_ai
            return None

        mock_world.get_component.side_effect = get_component_side_effect

        service.save_game("test_save.json")

        mock_json.dump.assert_called_once()
        args, _ = mock_json.dump.call_args
        data = args[0]

        assert data["money"] == 500
        assert len(data["entities"]) == 1
        assert data["entities"][0]["transform"]["x"] == 10
        assert data["entities"][0]["yukkuri"]["name"] == "Reimu"

class TestGameService:
    @pytest.fixture
    def mock_world(self):
        return MagicMock(spec=World)

    def test_find_best_item(self, mock_world):
        service = GameService(mock_world)

        # Setup mocked entities
        # Entity 1: Far away, correct stat
        # Entity 2: Close, correct stat
        # Entity 3: Close, wrong stat

        mock_world.get_entities_with.return_value = [1, 2, 3]

        def get_component(e, c):
            if c == Transform:
                if e == 1: return MagicMock(x=100, y=100)
                if e == 2: return MagicMock(x=10, y=10)
                if e == 3: return MagicMock(x=5, y=5)
            if c == ItemStats:
                if e == 1: return MagicMock(nutrition=10)
                if e == 2: return MagicMock(nutrition=10)
                if e == 3: return MagicMock(nutrition=0) # No nutrition
            return None

        mock_world.get_component.side_effect = get_component

        best_item = service.find_best_item((0, 0), "nutrition")
        assert best_item == 2

    def test_interact_with_item(self, mock_world):
        # Mock world.services
        mock_world.services = MagicMock()
        service = GameService(mock_world)

        consumer = 1
        item = 2

        mock_world.entity_exists.return_value = True

        y_stats = MagicMock(hunger=50, happiness=50)
        i_stats = MagicMock(nutrition=10, fun=5, comfort=0)

        def get_component(e, c):
            if e == consumer and c == YukkuriStats: return y_stats
            if e == item and c == ItemStats: return i_stats
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.has_component.return_value = True # For Transform check in destroy

        result = service.interact_with_item(consumer, item, consume=True)

        assert result is True
        assert y_stats.hunger == 40
        assert y_stats.happiness == 55
        mock_world.destroy_entity.assert_called_with(item)

    def test_interact_social_fight(self, mock_world):
        # Mock world.services
        mock_world.services = MagicMock()
        service = GameService(mock_world)

        p1 = 1
        p2 = 2

        mock_world.entity_exists.return_value = True

        p1_stats = MagicMock(health=100, happiness=100, stress=0)
        p2_stats = MagicMock(health=100, happiness=100, stress=0)

        def get_component(e, c):
            if e == p1 and c == YukkuriStats: return p1_stats
            if e == p2 and c == YukkuriStats: return p2_stats
            return None

        mock_world.get_component.side_effect = get_component

        service.interact_social(p1, p2, "Fight")

        assert p1_stats.health == 95
        assert p1_stats.happiness == 90
        assert p1_stats.stress == 10

        assert p2_stats.health == 95
