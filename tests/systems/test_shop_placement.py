"""
Regression tests for shop item purchasing and placement preview.

Verifies:
1. Entering placement mode via InputService sets state correctly.
2. The gameplay RenderingSystem pipeline uses the game-specific UIPass
   (which contains the placement ghost sprite logic), not the minimal
   engine-level UIPass.
3. PlacementRequestedEvent correctly spawns entities and deducts gold.
4. Insufficient funds prevent entity creation.
"""

import unittest
from unittest.mock import MagicMock, PropertyMock

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.game.events import PlacementRequestedEvent
from yukkuri_game.game.services import EconomyService, InputService
from yukkuri_game.game.systems.construction_system import ConstructionSystem
from yukkuri_game.game.systems.rendering.passes import (
    UIPass as GameUIPass,
    create_gameplay_pipeline,
)


class TestShopPlacementPipeline(unittest.TestCase):
    """Tests that the gameplay render pipeline contains the game UIPass."""

    def test_create_gameplay_pipeline_returns_game_ui_pass(self) -> None:
        """create_gameplay_pipeline() must include the game-layer UIPass.

        The game-layer UIPass handles placement preview (ghost sprite).
        The engine-layer UIPass only handles floating text and lacks
        the _process_placement_preview() method entirely.
        """
        from yukkuri_game.engine.rendering.pipeline import RenderPipeline

        pipeline = create_gameplay_pipeline()

        self.assertIsInstance(pipeline, RenderPipeline)

        ui_pass = pipeline.get_pass(GameUIPass)
        self.assertIsNotNone(
            ui_pass,
            "Gameplay pipeline must include the game-specific UIPass.",
        )
        self.assertTrue(
            hasattr(ui_pass, "_process_placement_preview"),
            "Game UIPass must implement _process_placement_preview().",
        )

    def test_gameplay_pipeline_pass_order(self) -> None:
        """Passes are in correct order: Culling, BG, Shadow, Sprite, Light, Occluder, UI."""
        from yukkuri_game.game.systems.rendering.passes import (
            BackgroundPass,
            CullingPass,
            LightPass,
            OccluderPass,
            ShadowPass,
            SpritePass,
        )

        pipeline = create_gameplay_pipeline()
        pass_types = [type(p) for p in pipeline.passes]

        expected_order = [
            CullingPass,
            BackgroundPass,
            ShadowPass,
            SpritePass,
            LightPass,
            OccluderPass,
            GameUIPass,
        ]
        self.assertEqual(
            pass_types,
            expected_order,
            "Gameplay pipeline passes are not in the expected order.",
        )


class TestInputServicePlacementMode(unittest.TestCase):
    """Tests that InputService placement mode state is managed correctly."""

    def setUp(self) -> None:
        """Sets up a fresh InputService instance."""
        self.input_service = InputService()

    def test_not_placing_by_default(self) -> None:
        """InputService is not in placement mode by default."""
        self.assertFalse(self.input_service.is_placing)

    def test_start_placement_sets_state(self) -> None:
        """start_placement() activates placing mode with correct attributes."""
        self.input_service.start_placement(
            type_id="cookie",
            cost=10,
            entity_type="item",
            image_name="cookie.png",
        )

        self.assertTrue(self.input_service.is_placing)
        self.assertEqual(self.input_service.place_type, "cookie")
        self.assertEqual(self.input_service.place_image_name, "cookie.png")
        self.assertEqual(self.input_service.place_cost, 10)
        self.assertEqual(self.input_service.place_entity_type, "item")

    def test_cancel_placement_clears_state(self) -> None:
        """cancel_placement() exits placement mode and clears all state."""
        self.input_service.start_placement(
            type_id="reimu",
            cost=100,
            entity_type="yukkuri",
            image_name="reimu.png",
        )
        self.assertTrue(self.input_service.is_placing)

        self.input_service.cancel_placement()
        self.assertFalse(self.input_service.is_placing)

    def test_start_placement_yukkuri(self) -> None:
        """start_placement() works correctly for yukkuri entity type."""
        self.input_service.start_placement(
            type_id="reimu",
            cost=150,
            entity_type="yukkuri",
            image_name="reimu.png",
        )

        self.assertTrue(self.input_service.is_placing)
        self.assertEqual(self.input_service.place_entity_type, "yukkuri")
        self.assertEqual(self.input_service.place_type, "reimu")
        self.assertEqual(self.input_service.place_cost, 150)


class TestShopPlacementPurchase(unittest.TestCase):
    """Integration tests for ConstructionSystem item and Yukkuri purchasing."""

    def setUp(self) -> None:
        """Sets up ConstructionSystem with mocked dependencies."""
        self.construction_system = ConstructionSystem()

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.economy_service_mock = MagicMock(spec=EconomyService)
        self.factory_mock = MagicMock(spec=EntityFactory)

        self.world_mock.services.get.side_effect = self._get_service
        # Trigger lazy init
        self.construction_system.update(self.world_mock, 0.0)

    def _get_service(self, service_type: type) -> object:
        """Returns the appropriate mock for a given service type."""
        if service_type is EventBus:
            return self.event_bus_mock
        if service_type is EconomyService:
            return self.economy_service_mock
        if service_type is EntityFactory:
            return self.factory_mock
        return None

    def test_buy_item_cookie_success(self) -> None:
        """Buying a cookie item deducts cost and spawns item entity."""
        type(self.economy_service_mock).money = PropertyMock(return_value=500)

        event = PlacementRequestedEvent(200.0, 300.0, "cookie", 10, "item")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_item.assert_called_once_with(
            "cookie", 200.0, 300.0
        )
        self.economy_service_mock.remove_money.assert_called_once_with(10)

    def test_buy_yukkuri_reimu_success(self) -> None:
        """Buying a reimu Yukkuri deducts cost and spawns Yukkuri entity."""
        type(self.economy_service_mock).money = PropertyMock(return_value=500)

        event = PlacementRequestedEvent(100.0, 100.0, "reimu", 100, "yukkuri")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_yukkuri.assert_called_once_with(
            "reimu", 100.0, 100.0
        )
        self.economy_service_mock.remove_money.assert_called_once_with(100)

    def test_buy_item_insufficient_funds_blocked(self) -> None:
        """Placement is blocked when the player has insufficient gold."""
        type(self.economy_service_mock).money = PropertyMock(return_value=5)

        event = PlacementRequestedEvent(200.0, 300.0, "cookie", 10, "item")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_item.assert_not_called()
        self.economy_service_mock.remove_money.assert_not_called()

    def test_buy_yukkuri_insufficient_funds_blocked(self) -> None:
        """Yukkuri placement is blocked when the player has insufficient gold."""
        type(self.economy_service_mock).money = PropertyMock(return_value=50)

        event = PlacementRequestedEvent(100.0, 100.0, "reimu", 100, "yukkuri")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_yukkuri.assert_not_called()
        self.economy_service_mock.remove_money.assert_not_called()

    def test_buy_bed_item_success(self) -> None:
        """Buying a bed item deducts cost and spawns item entity."""
        type(self.economy_service_mock).money = PropertyMock(return_value=500)

        event = PlacementRequestedEvent(400.0, 400.0, "bed", 100, "item")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_item.assert_called_once_with(
            "bed", 400.0, 400.0
        )
        self.economy_service_mock.remove_money.assert_called_once_with(100)

    def test_exact_funds_allows_purchase(self) -> None:
        """A player with exactly enough gold can complete a purchase."""
        type(self.economy_service_mock).money = PropertyMock(return_value=10)

        event = PlacementRequestedEvent(200.0, 300.0, "cookie", 10, "item")
        self.construction_system.on_placement_requested(event)

        self.factory_mock.create_item.assert_called_once()
        self.economy_service_mock.remove_money.assert_called_once_with(10)


if __name__ == "__main__":
    unittest.main()
