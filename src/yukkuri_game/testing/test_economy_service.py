import unittest
from yukkuri_game.game.services import EconomyService


class TestEconomyService(unittest.TestCase):
    def setUp(self) -> None:
        self.economy = EconomyService(1000)

    def test_initialization(self) -> None:
        self.assertEqual(self.economy.get_money(), 1000)

    def test_add_money(self) -> None:
        self.economy.add_money(500)
        self.assertEqual(self.economy.get_money(), 1500)

        with self.assertRaises(ValueError):
            self.economy.add_money(-100)

    def test_remove_money(self) -> None:
        success = self.economy.remove_money(500)
        self.assertTrue(success)
        self.assertEqual(self.economy.get_money(), 500)

        # Insufficient funds
        success = self.economy.remove_money(1000)
        self.assertFalse(success)
        self.assertEqual(self.economy.get_money(), 500)

        with self.assertRaises(ValueError):
            self.economy.remove_money(-100)

    def test_set_money(self) -> None:
        self.economy.set_money(5000)
        self.assertEqual(self.economy.get_money(), 5000)

        # Clamping
        self.economy.set_money(-100)
        self.assertEqual(self.economy.get_money(), 0)
