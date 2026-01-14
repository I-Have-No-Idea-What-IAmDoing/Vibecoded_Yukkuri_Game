"""
Flight System Module.
"""

import pymunk
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, Transform
from ..yukkuri_components import Flight, FlightState, Needs, EmotionalState


class FlightSystem(System):
    """
    System responsible for managing flight mechanics, including:
    - Stamina management (drain/recovery)
    - Altitude smoothing
    - State transitions
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates flight components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        for entity, (flight, controller, trans) in world.get_components_tuple(
            Flight, MovementController, Transform
        ):
            # 1. State Logic & Stamina
            if flight.state == FlightState.GROUNDED:
                # Recover stamina
                if flight.stamina < flight.max_stamina:
                    flight.stamina += flight.recovery_rate * dt
                    flight.stamina = min(flight.stamina, flight.max_stamina)
                
                # Snap altitude to 0
                flight.altitude = 0.0

            elif flight.state == FlightState.TAKEOFF:
                # Ascend
                flight.altitude += flight.vertical_speed * dt
                # Drain stamina
                self._drain_stamina(flight, flight.fly_cost, dt)
                
                if flight.altitude >= flight.max_altitude:
                    flight.altitude = flight.max_altitude
                    flight.state = FlightState.FLYING

            elif flight.state == FlightState.FLYING:
                # Maintain altitude
                flight.altitude = flight.max_altitude
                
                # Check movement for cost
                is_moving = controller.target_velocity.length_squared > 0.1
                cost = flight.fly_cost if is_moving else flight.hover_cost
                self._drain_stamina(flight, cost, dt)

            elif flight.state == FlightState.HOVERING:
                # Similar to flying but explicitly stationary intent
                flight.altitude = flight.max_altitude # Simplified
                self._drain_stamina(flight, flight.hover_cost, dt)

            elif flight.state == FlightState.LANDING:
                # Descend
                flight.altitude -= flight.vertical_speed * dt
                # Still costs some stamina to control descent? Or maybe free?
                # Let's say free to encourage landing.
                
                if flight.altitude <= 0.0:
                    flight.altitude = 0.0
                    flight.state = FlightState.GROUNDED

            elif flight.state == FlightState.SWOOPING:
                # Dive attack - rapid descent
                flight.altitude -= flight.vertical_speed * dt
                if flight.altitude <= 0.0:
                    flight.altitude = 0.0
                    flight.state = FlightState.GROUNDED
                    # Note: Attack logic (damage) is handled by the Behavior Action (EatPrey/Attack)
                    # This system just handles the "physics" of the dive.

            elif flight.state == FlightState.FALLING:
                # Rapid uncontrolled descent
                flight.altitude -= flight.vertical_speed * 1.5 * dt
                if flight.altitude <= 0.0:
                    flight.altitude = 0.0
                    flight.state = FlightState.GROUNDED
                    
                    # Apply Fall Damage and Stun
                    needs = world.try_get_component(entity, Needs)
                    if needs:
                        needs.health -= 20.0  # Fall damage
                        # TODO: Play impact sound/particle
                    
                    emotional = world.try_get_component(entity, EmotionalState)
                    if emotional:
                        emotional.stress += 50.0
                        emotional.happiness -= 20.0

    def _drain_stamina(self, flight: Flight, amount: float, dt: float) -> None:
        """Helper to drain stamina and handle exhaustion."""
        flight.stamina -= amount * dt
        if flight.stamina <= 0.0:
            flight.stamina = 0.0
            # Exhaustion -> Fall
            if flight.state not in (FlightState.GROUNDED, FlightState.LANDING):
                flight.state = FlightState.FALLING
