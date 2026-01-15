"""
Tests for Economy Service logic.
"""

import pytest
from yukkuri_game.game.services import EconomyService

@pytest.fixture
def economy_service() -> EconomyService:
    """
    Creates a new EconomyService.
    """
    return EconomyService()


def test_economy_initial_state(economy_service: EconomyService) -> None:
    """
    Tests initial money value.
    """
    assert economy_service.get_money() == 1000


def test_economy_add_money(economy_service: EconomyService) -> None:
    """
    Tests adding money.
    """
    economy_service.add_money(500)
    assert economy_service.get_money() == 1500


def test_economy_remove_money(economy_service: EconomyService) -> None:
    """
    Tests removing money.
    """
    assert economy_service.remove_money(500) is True
    assert economy_service.get_money() == 500

    assert economy_service.remove_money(1000) is False
    assert economy_service.get_money() == 500


def test_economy_set_money(economy_service: EconomyService) -> None:
    """
    Tests setting money directly.
    """
    economy_service.set_money(2000)
    assert economy_service.get_money() == 2000

    economy_service.set_money(-100)
    assert economy_service.get_money() == 0
