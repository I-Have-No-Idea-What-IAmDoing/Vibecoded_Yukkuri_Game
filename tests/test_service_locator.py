"""
Tests for the ServiceLocator pattern.
"""

import unittest
from yukkuri_game.engine.service_locator import ServiceLocator, ServiceNotFoundError


class TestServiceLocator(unittest.TestCase):
    """
    Tests the ServiceLocator functionality.
    """

    def setUp(self) -> None:
        """
        Sets up a fresh ServiceLocator for each test.
        """
        self.services = ServiceLocator()

    def test_register_and_get(self) -> None:
        """
        Tests registering and retrieving a service.
        """

        class MyService:
            pass

        service = MyService()
        self.services.register(service)
        self.assertIs(self.services.get(MyService), service)

    def test_register_with_type(self) -> None:
        """
        Tests registering a service under a specific base type.
        """

        class BaseService:
            pass

        class MyService(BaseService):
            pass

        service = MyService()
        self.services.register(service, service_type=BaseService)
        self.assertIs(self.services.get(BaseService), service)
        with self.assertRaises(ServiceNotFoundError):
            self.services.get(MyService)

    def test_try_get(self) -> None:
        """
        Tests safely trying to retrieve a service.
        """

        class MyService:
            pass

        self.assertIsNone(self.services.try_get(MyService))
        service = MyService()
        self.services.register(service)
        self.assertIs(self.services.try_get(MyService), service)

    def test_duplicate_registration(self) -> None:
        """
        Tests behavior when registering duplicate services (error vs replace).
        """

        class MyService:
            pass

        service1 = MyService()
        service2 = MyService()
        self.services.register(service1)
        with self.assertRaises(ValueError):
            self.services.register(service2)

        self.services.register(service2, replace=True)
        self.assertIs(self.services.get(MyService), service2)

    def test_get_not_found(self) -> None:
        """
        Tests that requesting a missing service raises an error.
        """

        class MyService:
            pass

        with self.assertRaises(ServiceNotFoundError):
            self.services.get(MyService)


if __name__ == "__main__":
    unittest.main()
