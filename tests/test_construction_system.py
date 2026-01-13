import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.construction_system import ConstructionSystem
from yukkuri_game.game.events import PlacementRequestedEvent
from yukkuri_game.game.services import EconomyService
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World


class TestConstructionSystem(unittest.TestCase):
    def setUp(self):
        self.construction_system = ConstructionSystem()

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.economy_service_mock = MagicMock(spec=EconomyService)
        self.factory_mock = MagicMock(spec=EntityFactory)

        self.world_mock.services.get.side_effect = self._get_service

        self.construction_system.update(self.world_mock, 0.0)

    def _get_service(self, service_type):
        if service_type == EventBus:
            return self.event_bus_mock
        elif service_type == EconomyService:
            return self.economy_service_mock
        elif service_type == EntityFactory:
            return self.factory_mock
        return None

    def test_placement_requested_success(self) -> None:
        # Setup adequate funds
        self.economy_service_mock.get_money.return_value = 200

        event = PlacementRequestedEvent(100.0, 100.0, "reimu", 100, "yukkuri")
        self.construction_system.on_placement_requested(event)

        # Verify money removed
        self.economy_service_mock.remove_money.assert_called_with(100)

        # Verify entity created
        self.factory_mock.create_yukkuri.assert_called_with("reimu", 100.0, 100.0)

    def test_placement_requested_insufficient_funds(self) -> None:
        # Setup inadequate funds
        self.economy_service_mock.get_money.return_value = 50

        event = PlacementRequestedEvent(100.0, 100.0, "reimu", 100, "yukkuri")
        self.construction_system.on_placement_requested(event)

        # Verify money NOT removed
        self.economy_service_mock.remove_money.assert_not_called()

        # Verify entity NOT created
        self.factory_mock.create_yukkuri.assert_not_called()

    def test_placement_requested_item(self) -> None:
        self.economy_service_mock.get_money.return_value = 200

        event = PlacementRequestedEvent(100.0, 100.0, "cookie", 10, "item")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_item.assert_called_with("cookie", 100.0, 100.0)


if __name__ == "__main__":
    unittest.main()
