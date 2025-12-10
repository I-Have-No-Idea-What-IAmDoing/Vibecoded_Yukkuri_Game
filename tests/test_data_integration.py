"""
Tests for Data Integration (msgspec models).
"""

import os
import sys
import unittest
import msgspec

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from yukkuri_game.engine.data_models import (
    YukkuriData,
    ItemData,
    AIData,
)
from yukkuri_game.engine.resource_manager import ResourceManager


class TestDataIntegration(unittest.TestCase):
    """
    Tests the correct parsing of TOML data into msgspec models.
    """

    def setUp(self) -> None:
        """
        Sets up the test environment.
        """
        self.resource_manager = ResourceManager()

    def test_yukkuri_model(self) -> None:
        """
        Tests that YukkuriData correctly decodes valid TOML.
        """
        toml_data = """
        [yukkuris.test]
        name = "Test"
        image = "test.png"
        width = 10
        height = 10
        max_health = 100
        base_happiness = 50
        """

        decoded = msgspec.toml.decode(toml_data.encode("utf-8"), type=YukkuriData)
        self.assertIn("test", decoded.yukkuris)
        self.assertEqual(decoded.yukkuris["test"].name, "Test")
        self.assertEqual(decoded.yukkuris["test"].width, 10)

    def test_item_model(self) -> None:
        """
        Tests that ItemData correctly decodes valid TOML.
        """
        toml_data = """
        [items.testitem]
        name = "Test Item"
        image = "item.png"
        width = 5
        height = 5
        cost = 50
        is_portable = true
        nutrition = 10
        """

        decoded = msgspec.toml.decode(toml_data.encode("utf-8"), type=ItemData)
        self.assertIn("testitem", decoded.items)
        self.assertEqual(decoded.items["testitem"].cost, 50)
        self.assertEqual(decoded.items["testitem"].nutrition, 10)
        self.assertIsNone(decoded.items["testitem"].fun)

    def test_ai_model(self) -> None:
        """
        Tests that AIData correctly decodes valid TOML.
        """
        toml_data = """
        [actions.testaction]
        weight = 1.5
        [actions.testaction.effects]
        type = "test_effect"

        [[actions.testaction.considerations]]
        name = "Test Consider"
        input = "input"
        curve = "linear"
        """

        decoded = msgspec.toml.decode(toml_data.encode("utf-8"), type=AIData)
        self.assertIn("testaction", decoded.actions)
        self.assertEqual(decoded.actions["testaction"].weight, 1.5)
        self.assertEqual(decoded.actions["testaction"].effects.type, "test_effect")
        self.assertEqual(len(decoded.actions["testaction"].considerations), 1)
        self.assertEqual(
            decoded.actions["testaction"].considerations[0].name, "Test Consider"
        )

    def test_malformed_data(self) -> None:
        """
        Tests that validation errors are raised for missing required fields.
        """
        toml_data = """
        [yukkuris.bad]
        name = "Bad"
        # Missing required fields
        """
        with self.assertRaises(msgspec.ValidationError):
            msgspec.toml.decode(toml_data.encode("utf-8"), type=YukkuriData)

    def test_wrong_type(self) -> None:
        """
        Tests that validation errors are raised for incorrect data types.
        """
        toml_data = """
        [yukkuris.bad]
        name = 123 # Should be string
        image = "test.png"
        width = 10
        height = 10
        max_health = 100
        base_happiness = 50
        """
        with self.assertRaises(msgspec.ValidationError):
            msgspec.toml.decode(toml_data.encode("utf-8"), type=YukkuriData)


if __name__ == "__main__":
    unittest.main()
