import sys
from unittest.mock import MagicMock

# Mock pygame before importing modules that use it
mock_pygame = MagicMock()
sys.modules["pygame"] = mock_pygame
sys.modules["pygame.locals"] = MagicMock()
# Mock pygame_gui
sys.modules["pygame_gui"] = MagicMock()
sys.modules["pygame_light2d"] = MagicMock()

import pytest
from unittest.mock import MagicMock

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import Flight, FlightState
from yukkuri_game.game.components import Transform
from yukkuri_game.game.systems.flight_system import FlightSystem


@pytest.fixture
def world():
    return World()


@pytest.fixture
def flight_system(world):
    fs = FlightSystem()
    world.add_system(fs)
    return fs


@pytest.fixture
def flying_entity(world):
    entity = world.create_entity()
    flight = Flight(
        state=FlightState.FLYING,
        stamina=100.0,
        max_stamina=100.0,
        altitude=60.0,
        max_altitude=60.0,
        fly_cost=10.0,
        hover_cost=2.0,
        recovery_rate=5.0,
    )
    transform = Transform(x=0, y=0)
    world.add_component(entity, flight)
    world.add_component(entity, transform)
    return entity, flight, transform


def test_flight_drain(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity

    # Simulate 1 second
    flight_system.update(world, 1.0)

    # Should have drained 10 stamina (fly_cost)
    assert flight.stamina == 90.0


def test_hover_drain(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.state = FlightState.HOVERING

    flight_system.update(world, 1.0)

    # Should have drained 2 stamina (hover_cost)
    assert flight.stamina == 98.0


def test_recovery(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.state = FlightState.GROUNDED
    flight.stamina = 50.0

    flight_system.update(world, 1.0)

    # Should have recovered 5 stamina (recovery_rate)
    assert flight.stamina == 55.0


def test_recovery_cap(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.state = FlightState.GROUNDED
    flight.stamina = 99.0

    flight_system.update(world, 1.0)

    assert flight.stamina == 100.0


def test_crash_when_out_of_stamina(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.stamina = 5.0
    flight.fly_cost = 10.0

    # Updates: drain 10 -> -5 -> clamp to 0 -> State FALLING
    flight_system.update(world, 1.0)

    assert flight.stamina == 0.0
    assert flight.state == FlightState.FALLING


def test_falling_mechanics(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.state = FlightState.FALLING
    flight.altitude = 100.0
    flight.vertical_speed = 10.0

    # FALLING falls at 2x vertical speed -> 20 units/sec
    flight_system.update(world, 1.0)

    assert flight.altitude == 80.0

    # Test landing from fall
    flight.altitude = 10.0
    flight_system.update(world, 1.0)  # -20 -> -10 -> clamp 0

    assert flight.altitude == 0.0
    assert flight.state == FlightState.GROUNDED


def test_takeoff(flight_system, world, flying_entity):
    entity, flight, _ = flying_entity
    flight.state = FlightState.TAKEOFF
    flight.altitude = 0.0
    flight.max_altitude = 100.0
    flight.vertical_speed = 10.0

    flight_system.update(world, 1.0)

    assert flight.altitude == 10.0
    assert flight.state == FlightState.TAKEOFF

    # Near max logic
    flight.altitude = 96.0  # 96% of 100
    flight_system.update(world, 1.0)

    assert flight.state == FlightState.FLYING
