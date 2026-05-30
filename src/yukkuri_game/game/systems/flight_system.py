"""
Flight System Module.
"""

from ...engine.ecs import System, World
from ..components import (
    EmotionalState,
    Needs,
    YukkuriStats,
)
from ...engine.components import (
    Flight,
    FlightState,
    Transform,
)
from ..skill_constants import SkillId
from ..skill_service import SkillService


class FlightSystem(System):
    """
    System responsible for managing flight mechanics:
    - Stamina management (drain/recovery).
    - Altitude updates.
    - State transitions (e.g. running out of stamina).
    """

    # Fall consequences
    FALL_DAMAGE = 10.0  # Health lost when falling from exhaustion
    FALL_STRESS = 20.0  # Stress gained when falling
    SWOOP_ALTITUDE = 5.0  # Target altitude during swoop attack

    def update(self, world: World, dt: float) -> None:
        """
        Updates flight components.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        for entity, (flight, transform) in world.get_components_tuple(
            Flight, Transform
        ):
            self._process_flight(world, entity, flight, transform, dt)

    def _process_flight(
        self, world: World, entity: int, flight: Flight, transform: Transform, dt: float
    ) -> None:
        skill_service = world.services.try_get(SkillService)

        stats = world.try_get_component(entity, YukkuriStats)
        agility = stats.agility if stats else 1.0

        # 1. Stamina Management
        if flight.state in (
            FlightState.FLYING,
            FlightState.TAKEOFF,
            FlightState.SWOOPING,
        ):
            # Drain stamina (Fly cost) - More agile = more efficient
            flight.stamina -= (flight.fly_cost / agility) * dt

            # Award Athleticism XP (Flying is hard work)
            if skill_service:
                skill_service.add_xp(entity, SkillId.ATHLETICS, 2.0 * dt)

        elif flight.state == FlightState.HOVERING:
            # Drain stamina (Hover cost)
            flight.stamina -= (flight.hover_cost / agility) * dt

            if skill_service:
                skill_service.add_xp(entity, SkillId.ATHLETICS, 1.0 * dt)

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
            target_altitude = self.SWOOP_ALTITUDE  # Swoop low but not touching ground
        elif flight.state == FlightState.FALLING:
            target_altitude = 0.0
            flight.altitude -= flight.vertical_speed * 2.0 * dt
            if flight.altitude <= 0:
                flight.altitude = 0.0
                flight.state = FlightState.GROUNDED

                # Apply Fall Damage and Stun - Agile entities take less damage
                needs = world.try_get_component(entity, Needs)
                if needs:
                    needs.health -= self.FALL_DAMAGE / agility

                emotional = world.try_get_component(entity, EmotionalState)
                if emotional:
                    emotional.stress += self.FALL_STRESS / agility

            return

        # Interpolate Altitude
        diff = target_altitude - flight.altitude
        if abs(diff) > 0.01:
            change = flight.vertical_speed * agility * dt
            if abs(diff) < change:
                flight.altitude = target_altitude
            else:
                flight.altitude += change if diff > 0 else -change
