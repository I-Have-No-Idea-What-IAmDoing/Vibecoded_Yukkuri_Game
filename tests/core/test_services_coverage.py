import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from yukkuri_game.game.services import (
    TimeService,
    EconomyService,
    InputService,
    PersistenceService,
    GameService,
)
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform
from yukkuri_game.game.components import (
    YukkuriStats,
    Needs,
    ItemStats,
    AIState,
    EmotionalState,
    Skills,
)
from yukkuri_game.game.skill_constants import SkillId


class TestTimeService:
    def test_time_elapsed(self) -> None:
        service = TimeService()
        assert service.time_elapsed == 0.0

        service.time_elapsed = 1.5
        assert service.time_elapsed == 1.5

        service.time_elapsed = 10.0
        assert service.time_elapsed == 10.0


class TestEconomyService:
    def test_initial_money(self) -> None:
        service = EconomyService(initial_money=500)
        assert service.money == 500

    def test_add_money(self) -> None:
        service = EconomyService(100)
        service.add_money(50)
        assert service.money == 150

        with pytest.raises(ValueError):
            service.add_money(-10)

    def test_remove_money(self) -> None:
        service = EconomyService(100)
        assert service.remove_money(50) is True
        assert service.money == 50

        assert service.remove_money(60) is False
        assert service.money == 50

        with pytest.raises(ValueError):
            service.remove_money(-10)

    def test_set_money(self) -> None:
        service = EconomyService(100)
        service.set_money(200)
        assert service.money == 200

        service.set_money(-50)
        assert service.money == 0


class TestInputService:
    def test_placement_mode(self) -> None:
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

    def test_cleaning_mode(self) -> None:
        service = InputService()
        service.start_cleaning()
        assert service.is_cleaning is True
        assert service.is_placing is False

        service.stop_cleaning()
        assert service.is_cleaning is False

    def test_cleaning_interrupts_placement(self) -> None:
        service = InputService()
        service.start_placement("t", 10, "i")
        service.start_cleaning()
        assert service.is_cleaning is True
        assert service.is_placing is False


class TestPersistenceService:
    @pytest.fixture
    def mock_world(self):
        return MagicMock(spec=World)

    def test_save_creates_two_files(self, tmp_path, mock_world):
        """save_game writes both .level.msgpack and .global.json."""
        mock_world.services = MagicMock()

        mock_economy = MagicMock(spec=EconomyService)
        type(mock_economy).money = PropertyMock(return_value=500)

        mock_time = MagicMock()
        mock_time.time_elapsed = 99.5

        mock_world.services.try_get.side_effect = (
            lambda t: mock_economy if t == EconomyService
            else mock_time if t == TimeService
            else None
        )

        service = PersistenceService(mock_world, save_dir=str(tmp_path))

        # Patch _build_serializer so we don't need a real World
        mock_serializer = MagicMock()
        with patch.object(service, "_build_serializer", return_value=mock_serializer):
            service.save_game("mysave.json")

        import json
        global_file = tmp_path / "mysave.global.json"
        level_file = tmp_path / "mysave.level.msgpack"

        assert global_file.exists(), "global.json must be written"
        assert mock_serializer.save_to_file.called, "level.msgpack must be written"

        data = json.loads(global_file.read_text())
        assert data["money"] == 500
        assert data["time"] == 99.5

    def test_load_returns_false_when_files_missing(self, tmp_path, mock_world):
        """load_game returns False when save files don't exist."""
        service = PersistenceService(mock_world, save_dir=str(tmp_path))
        result = service.load_game("nonexistent.json")
        assert result is False

    def test_load_restores_global_state(self, tmp_path, mock_world):
        """load_game restores economy and time from global.json."""
        import json

        mock_world.services = MagicMock()

        mock_economy = MagicMock(spec=EconomyService)
        mock_time = MagicMock()

        mock_world.services.try_get.side_effect = (
            lambda t: mock_economy if t == EconomyService
            else mock_time if t == TimeService
            else None
        )

        service = PersistenceService(mock_world, save_dir=str(tmp_path))

        # Write stub files
        global_file = tmp_path / "mysave.global.json"
        level_file = tmp_path / "mysave.level.msgpack"
        global_file.write_text(json.dumps({"money": 1234, "time": 42.0}))
        level_file.write_bytes(b"")  # stub; serializer will be mocked

        mock_serializer = MagicMock()
        with patch.object(service, "_build_serializer", return_value=mock_serializer):
            result = service.load_game("mysave.json")

        assert result is True
        mock_economy.set_money.assert_called_once_with(1234)
        assert mock_time.time_elapsed == 42.0
        mock_serializer.load_from_file.assert_called_once()


class TestGameService:
    @pytest.fixture
    def mock_world(self):
        # We need world.services to exist
        world = MagicMock(spec=World)
        world.services = MagicMock()
        # Mock try_get for SpatialService
        world.services.try_get.return_value = None
        return world

    def test_find_best_item(self, mock_world):
        service = GameService(mock_world)

        # Setup mocked entities
        # Entity 1: Far away, correct stat
        # Entity 2: Close, correct stat
        # Entity 3: Close, wrong stat

        mock_world.get_components_tuple.return_value = [
            (1, (MagicMock(nutrition=10), MagicMock(x=100, y=100))),
            (2, (MagicMock(nutrition=10), MagicMock(x=10, y=10))),
            (3, (MagicMock(nutrition=0), MagicMock(x=5, y=5))),
        ]

        # Keeping get_component side_effect just in case it's used elsewhere
        def get_component(e, c):
            if c == Transform:
                if e == 1:
                    return MagicMock(x=100, y=100)
                if e == 2:
                    return MagicMock(x=10, y=10)
                if e == 3:
                    return MagicMock(x=5, y=5)
            if c == ItemStats:
                if e == 1:
                    return MagicMock(nutrition=10)
                if e == 2:
                    return MagicMock(nutrition=10)
                if e == 3:
                    return MagicMock(nutrition=0)  # No nutrition
            return None

        mock_world.get_component.side_effect = get_component

        # Test basic finding
        best_item = service.find_best_item((0, 0), "nutrition")
        assert best_item == 2

    def test_find_best_item_with_scavenging(self, mock_world):
        """Test finding item with scavenging skill increasing radius"""
        service = GameService(mock_world)

        # Base radius is 500
        # Item at 600 distance
        # Searcher with Level 3 Scavenging -> 500 + 3*50 = 650 radius

        searcher_id = 99
        mock_world.entity_exists.return_value = True

        skills = Skills()
        # Manually set up skill state since Skills is a dataclass
        from yukkuri_game.game.components import SkillState

        skills.states[SkillId.SCAVENGING] = SkillState(level=3, current_xp=500.0)

        item_id = 10
        item_pos = MagicMock(x=600, y=0)
        item_stats = MagicMock(nutrition=10)

        mock_world.get_components_tuple.return_value = [(item_id, (item_stats, item_pos))]

        # Also need Personality for compatibility check in _update_opinion
        p_pers = MagicMock()
        p_pers.traits = []
        p_pers.axis = MagicMock()
        p_pers.axis.kindness = 0  # Ensure kindness is an int for calculation

        # Need TraitService imported

        def get_component(e, c):
            if e == searcher_id and c == Skills:
                return skills
            if e == item_id and c == Transform:
                return item_pos
            if e == item_id and c == ItemStats:
                return item_stats
            if e == searcher_id and c == YukkuriStats:
                return MagicMock()  # Needs stats
            return None

        mock_world.get_component.side_effect = get_component

        # Should find it with skill
        best_item = service.find_best_item((0, 0), "nutrition", searcher_id=searcher_id)
        assert best_item == item_id

        # Should NOT find it without skill (mock no skills)
        def get_component_no_skill(e, c):
            if e == searcher_id and c == Skills:
                return None
            if e == item_id and c == Transform:
                return item_pos
            if e == item_id and c == ItemStats:
                return item_stats
            return None

        mock_world.get_component.side_effect = get_component_no_skill
        best_item_fail = service.find_best_item(
            (0, 0), "nutrition", searcher_id=searcher_id
        )
        assert best_item_fail == -1  # Corrected to -1 for failure
