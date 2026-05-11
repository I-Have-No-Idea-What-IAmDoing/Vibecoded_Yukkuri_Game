"""
Unit tests for Flight component and collision filtering.
"""

from yukkuri_game.game.components import Flight, FlightState, Predator
from yukkuri_game.game.collision_constants import CollisionCategories


class TestFlightComponent:
    """Tests for the Flight component."""

    def test_flight_default_values(self):
        """Verify default values are correctly set."""
        flight = Flight()

        assert flight.altitude == 0.0
        assert flight.max_altitude == 60.0
        assert flight.stamina == 100.0
        assert flight.state == FlightState.GROUNDED

    def test_flight_state_enum_values(self):
        """Verify all FlightState enum values exist."""
        assert FlightState.GROUNDED.value == 0
        assert FlightState.TAKEOFF.value == 1
        assert FlightState.FLYING.value == 2
        assert FlightState.HOVERING.value == 3
        assert FlightState.LANDING.value == 4
        assert FlightState.SWOOPING.value == 5
        assert FlightState.FALLING.value == 6

    def test_flight_custom_values(self):
        """Verify custom values can be set."""
        flight = Flight(
            altitude=30.0,
            max_altitude=80.0,
            stamina=50.0,
            state=FlightState.FLYING,
        )

        assert flight.altitude == 30.0
        assert flight.max_altitude == 80.0
        assert flight.stamina == 50.0
        assert flight.state == FlightState.FLYING


class TestPredatorComponent:
    """Tests for the Predator component."""

    def test_predator_default_values(self):
        """Verify default values are correctly set."""
        predator = Predator()

        assert predator.prey_tags == set()
        assert predator.prey_sense_radius == 300.0
        assert predator.hunger_threshold == 60.0
        assert predator.aggression == 1.0
        assert predator.dps == 20.0

    def test_predator_prey_tags(self):
        """Verify prey_tags can be set."""
        predator = Predator(prey_tags={"Reimu", "Weak"})

        assert "Reimu" in predator.prey_tags
        assert "Weak" in predator.prey_tags
        assert len(predator.prey_tags) == 2


class TestCollisionCategories:
    """Tests for collision category bitmasks."""

    def test_new_categories_exist(self):
        """Verify new collision categories are defined."""
        CC = CollisionCategories

        assert CC.GROUND_UNIT == 0b0000_0001
        assert CC.FLYING_UNIT == 0b0000_0010
        assert CC.LOW_OBSTACLE == 0b0000_1000
        assert CC.HIGH_OBSTACLE == 0b0001_0000
        assert CC.WATER == 0b0010_0000
        assert CC.SENSOR == 0b1000_0000



    def test_categories_are_unique_bits(self):
        """Verify all categories use unique bits."""
        CC = CollisionCategories

        all_cats = [
            CC.GROUND_UNIT,
            CC.FLYING_UNIT,
            CC.ITEM,
            CC.LOW_OBSTACLE,
            CC.HIGH_OBSTACLE,
            CC.WATER,
            CC.POOP,
            CC.SENSOR,
        ]

        # Check no duplicates
        assert len(all_cats) == len(set(all_cats))

        # Check all are single-bit or unique combinations
        combined = 0
        for cat in all_cats:
            assert cat & combined == 0, f"{cat} overlaps with existing categories"
            combined |= cat
