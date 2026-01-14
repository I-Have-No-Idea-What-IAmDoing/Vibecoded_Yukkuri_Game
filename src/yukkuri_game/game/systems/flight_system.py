"""
Flight System Module.
"""

from ...engine.ecs import System, World
from ..components import Transform
from ..yukkuri_components import Flight, FlightState


class FlightSystem(System):
    """
    System responsible for managing flight mechanics:
    - Stamina management (drain/recovery).
    - Altitude updates.
    - State transitions (e.g. running out of stamina).
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates flight components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Ensure we iterate over all entities with Flight components
        # Note: Transform is usually present but not strictly required for logic unless we modify it?
        # Actually we modify flight.altitude which RenderSystem uses.
        # But we do need DT.

        for entity, (flight, transform) in world.get_components_tuple(
            Flight, Transform
        ):
            self._process_flight(flight, transform, dt)

    def _process_flight(self, flight: Flight, transform: Transform, dt: float) -> None:
        # 1. Stamina Management
        if flight.state in (
            FlightState.FLYING,
            FlightState.TAKEOFF,
            FlightState.SWOOPING,
        ):
            # Drain stamina (Fly cost)
            flight.stamina -= flight.fly_cost * dt
        elif flight.state == FlightState.HOVERING:
            # Drain stamina (Hover cost)
            flight.stamina -= flight.hover_cost * dt
        elif flight.state == FlightState.GROUNDED:
            # Recovery
            flight.stamina += flight.recovery_rate * dt

        # Clamp stamina
        flight.stamina = max(0.0, min(flight.max_stamina, flight.stamina))

        # 2. State Logic & Transitions
        if flight.stamina <= 0 and flight.state != FlightState.GROUNDED:
            # Out of stamina! Fall!
            flight.state = FlightState.FALLING

        # Altitude Logic
        target_altitude = 0.0

        if flight.state == FlightState.GROUNDED:
            target_altitude = 0.0
        elif flight.state == FlightState.TAKEOFF:
            target_altitude = flight.max_altitude
            if flight.altitude >= flight.max_altitude * 0.95:
                flight.state = FlightState.FLYING
        elif flight.state == FlightState.FLYING or flight.state == FlightState.HOVERING:
            target_altitude = flight.max_altitude
        elif flight.state == FlightState.LANDING:
            target_altitude = 0.0
            if flight.altitude <= 0.1:
                flight.state = FlightState.GROUNDED
                flight.altitude = 0.0
        elif flight.state == FlightState.SWOOPING:
            target_altitude = 5.0  # Swoop low but not touching ground
            # Don't auto-transition out of swooping; AI controls that (unless hit/stamina out)
        elif flight.state == FlightState.FALLING:
            target_altitude = 0.0
            # Fall fast
            flight.altitude -= flight.vertical_speed * 2.0 * dt
            if flight.altitude <= 0:
                flight.altitude = 0.0
                flight.state = FlightState.GROUNDED
                # Apply stun? (Future work)
            return  # Skip smooth interpolation for falling

        # Interpolate Altitude
        diff = target_altitude - flight.altitude
        if abs(diff) > 0.01:
            change = flight.vertical_speed * dt
            if abs(diff) < change:
                flight.altitude = target_altitude
            else:
                flight.altitude += change if diff > 0 else -change
