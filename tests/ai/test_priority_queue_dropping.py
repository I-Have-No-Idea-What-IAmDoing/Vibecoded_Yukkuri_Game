import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.game.ai.navigation_service import NavigationService


class TestNavigationServiceCongestion(unittest.TestCase):
    def test_drops_low_priority_when_full(self):
        service = NavigationService(100, 100)

        # Fill queue with 51 items
        # We can directly access queue or push via request_path
        # request_path is async (non-blocking put), just puts in queue.

        # Mock grid to avoid errors in coordinate conversion (though default 100x100 is fine)

        # Fill up to 51
        for i in range(51):
            service.request_path(i, (0, 0), (10, 10), priority=1)

        self.assertEqual(service.request_queue.qsize(), 51)

        # Try to add Low Priority (3)
        service.request_path(999, (0, 0), (10, 10), priority=3)

        # Should be dropped, size remains 51
        self.assertEqual(service.request_queue.qsize(), 51)

        # Try to add High Priority (0)
        service.request_path(888, (0, 0), (10, 10), priority=0)

        # Should be accepted, size becomes 52
        self.assertEqual(service.request_queue.qsize(), 52)

        service.shutdown()


if __name__ == "__main__":
    unittest.main()
