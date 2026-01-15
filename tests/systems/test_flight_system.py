"""
Consolidated unit tests for the Flight System.
Merged from test_flight_system.py and test_flight_system_game.py.
"""

import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.flight_system import FlightSystem
from yukkuri_game.game.yukkuri_components import (
    Flight,
    FlightState,
    Needs,
    EmotionalState,
)
from yukkuri_game.game.components import MovementController, Transform


class TestFlightSystem:
    """Tests for FlightSystem logic."""

    @pytest.fixture
    def world(self):
        return World()

    @pytest.fixture
    def system(self):
        return FlightSystem()

    def create_flying_entity(
        self, world, state=FlightState.GROUNDED, stamina=100.0, altitude=0.0
    ):
        entity = world.create_entity()
        flight = Flight(state=state, stamina=stamina, altitude=altitude)
        controller = MovementController()
        transform = Transform(x=0, y=0)

        world.add_component(entity, flight)
        world.add_component(entity, controller)
        world.add_component(entity, transform)
        return entity, flight

    # --- Stamina Tests ---
    def test_stamina_recovery_when_grounded(self, system, world):
        """Stamina should recover when grounded."""
        _, flight = self.create_flying_entity(world, FlightState.GROUNDED, stamina=50.0)

        system.update(world, dt=1.0)

        # 50 + 10 * 1.0 = 60
        assert flight.stamina == 60.0
        assert flight.altitude == 0.0

    def test_recovery_cap(self, system, world):
        """Stamina should not exceed max."""
        _, flight = self.create_flying_entity(world, FlightState.GROUNDED, stamina=99.0)
        flight.max_stamina = 100.0

        system.update(world, dt=1.0)

        assert flight.stamina == 100.0

    def test_flying_drains_stamina(self, system, world):
        """Flying should drain stamina."""
        entity, flight = self.create_flying_entity(world, FlightState.FLYING, stamina=100.0)
        flight.fly_cost = 5.0
        flight.hover_cost = 1.0

        # Simulate moving
        controller = world.get_component(entity, MovementController)
        controller.target_velocity = pymunk.Vec2d(10, 0)

        system.update(world, dt=1.0)

        assert flight.stamina == 95.0

    def test_hovering_drains_less_stamina(self, system, world):
        """Hovering (not moving) should drain less stamina."""
        entity, flight = self.create_flying_entity(world, FlightState.FLYING, stamina=100.0)
        flight.fly_cost = 5.0
        flight.hover_cost = 1.0

        # Simulate NOT moving
        controller = world.get_component(entity, MovementController)
        controller.target_velocity = pymunk.Vec2d(0, 0)

        system.update(world, dt=1.0)

        assert flight.stamina == 99.0

    def test_hover_state_drains_stamina(self, system, world):
        """HOVERING state should drain hover_cost stamina."""
        _, flight = self.create_flying_entity(world, FlightState.HOVERING, stamina=100.0)
        flight.hover_cost = 2.0

        system.update(world, dt=1.0)

        assert flight.stamina == 98.0

    # --- Takeoff Tests ---
    def test_takeoff_ascends_and_drains_stamina(self, system, world):
        """Takeoff should increase altitude and drain stamina."""
        _, flight = self.create_flying_entity(
            world, FlightState.TAKEOFF, stamina=100.0, altitude=0.0
        )
        flight.max_altitude = 100.0
        flight.vertical_speed = 10.0
        flight.fly_cost = 5.0

        system.update(world, dt=1.0)

        assert flight.altitude == 10.0
        assert flight.stamina == 95.0
        assert flight.state == FlightState.TAKEOFF

    def test_transition_to_flying_at_max_altitude(self, system, world):
        """Should switch to FLYING when reaching max altitude."""
        _, flight = self.create_flying_entity(world, FlightState.TAKEOFF, altitude=95.0)
        flight.max_altitude = 100.0
        flight.vertical_speed = 10.0

        system.update(world, dt=1.0)

        assert flight.altitude == 100.0
        assert flight.state == FlightState.FLYING

    # --- Landing Tests ---
    def test_landing_descends(self, system, world):
        """Landing should decrease altitude."""
        _, flight = self.create_flying_entity(world, FlightState.LANDING, altitude=50.0)
        flight.vertical_speed = 10.0

        system.update(world, dt=1.0)

        assert flight.altitude == 40.0

    def test_landing_reaches_ground(self, system, world):
        """Landing at 0 altitude switches to GROUNDED."""
        _, flight = self.create_flying_entity(world, FlightState.LANDING, altitude=5.0)
        flight.vertical_speed = 10.0

        system.update(world, dt=1.0)

        assert flight.altitude == 0.0

    # --- Falling Tests ---
    def test_exhaustion_causes_fall(self, system, world):
        """Running out of stamina should trigger FALLING state."""
        entity, flight = self.create_flying_entity(world, FlightState.FLYING, stamina=2.0)
        flight.fly_cost = 5.0

        # Simulate moving
        controller = world.get_component(entity, MovementController)
        controller.target_velocity = pymunk.Vec2d(10, 0)

        system.update(world, dt=1.0)

        assert flight.stamina == 0.0
        assert flight.state == FlightState.FALLING

    def test_falling_mechanics(self, system, world):
        """Falling should decrease altitude at accelerated rate."""
        _, flight = self.create_flying_entity(world, FlightState.FALLING, altitude=100.0)
        flight.vertical_speed = 10.0

        system.update(world, dt=1.0)

        # FALLING falls at 1.5x vertical speed -> 15 units/sec
        assert flight.altitude < 100.0

    def test_fall_damage_and_stun(self, system, world):
        """Falling to ground should deal damage and stun."""
        entity, flight = self.create_flying_entity(
            world, FlightState.FALLING, altitude=5.0
        )
        flight.vertical_speed = 10.0

        # Add Needs and EmotionalState
        needs = Needs(max_health=100.0, health=100.0)
        emotional = EmotionalState(stress=0.0, happiness=50.0)
        world.add_component(entity, needs)
        world.add_component(entity, emotional)

        system.update(world, dt=1.0)

        assert flight.altitude == 0.0
        assert flight.state == FlightState.GROUNDED

        # Check damage
        assert needs.health < 100.0

        # Check stun (stress increase)
        assert emotional.stress > 0.0

    # --- Swooping Tests ---
    def test_swoop_descends_rapidly(self, system, world):
        """Swooping should descend faster than landing."""
        _, flight = self.create_flying_entity(
            world, FlightState.SWOOPING, altitude=100.0
        )
        flight.vertical_speed = 50.0

        system.update(world, dt=1.0)

        # 100 - 50 * 1.0 = 50
        assert flight.altitude == 50.0
