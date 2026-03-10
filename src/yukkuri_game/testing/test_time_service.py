import unittest
from yukkuri_game.game.services import TimeService


class TestTimeService(unittest.TestCase):
    def setUp(self) -> None:
        self.time_service = TimeService()

    def test_initialization(self) -> None:
        self.assertEqual(self.time_service.time_elapsed, 0.0)
        self.assertEqual(self.time_service.scale, 60.0)
        self.assertEqual(self.time_service.game_speed, 1.0)

    def test_update(self) -> None:
        # Physics dt = 1.0, scale = 60.0, speed = 1.0 -> Game dt = 60.0
        game_dt = self.time_service.update(1.0)
        self.assertEqual(game_dt, 60.0)
        self.assertEqual(self.time_service.time_elapsed, 60.0)

    def test_game_speed(self) -> None:
        self.time_service.game_speed = 2.0
        # Physics dt = 1.0, scale = 60.0, speed = 2.0 -> Game dt = 120.0
        game_dt = self.time_service.update(1.0)
        self.assertEqual(game_dt, 120.0)

    def test_day_night_cycle(self) -> None:
        # Day length is 86400 seconds (24 hours)
        # Day starts at 6.0, Night at 20.0 by default

        # Time 0 -> Hour 0 -> Night
        self.assertTrue(self.time_service.is_night)

        # Advance to 7 AM (7 * 3600 = 25200)
        self.time_service.time_elapsed = 25200
        self.assertFalse(self.time_service.is_night)

        # Advance to 9 PM (21 * 3600 = 75600)
        self.time_service.time_elapsed = 75600
        self.assertTrue(self.time_service.is_night)

    def test_day_counter(self) -> None:
        self.assertEqual(self.time_service.day, 1)

        # Advance slightly past one day
        self.time_service.time_elapsed = 86401.0
        self.assertEqual(self.time_service.day, 2)
