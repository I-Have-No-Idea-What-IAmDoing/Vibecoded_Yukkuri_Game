"""
Time Service for tracking game time.
"""

class TimeService:
    """
    Service responsible for tracking game time.

    Game time runs at a configurable scale relative to physics time.
    Default 60x means 1 physics second = 1 game minute.

    Attributes:
        _time_elapsed (float): The total elapsed game time in seconds.
        _scale (float): Game seconds per physics second.
        _day_start_hour (float): Hour when day begins.
        _night_start_hour (float): Hour when night begins.
        _game_speed (float): User-adjustable multiplier for game time progression.
    """

    GAME_DAY_LENGTH: float = 86400.0  # 24 hours in game seconds

    def __init__(
        self,
        time_elapsed: float = 0.0,
        scale: float = 60.0,
        day_start_hour: float = 6.0,
        night_start_hour: float = 20.0,
    ) -> None:
        """
        Initializes the TimeService.

        Args:
            time_elapsed (float): The initial elapsed game time. Defaults to 0.0.
            scale (float): The game time scale factor. Defaults to 60.0.
            day_start_hour (float): The hour (0-24) when day starts. Defaults to 6.0.
            night_start_hour (float): The hour (0-24) when night starts. Defaults to 20.0.
        """
        self._time_elapsed = time_elapsed
        self._scale = scale
        self._day_start_hour = day_start_hour
        self._night_start_hour = night_start_hour
        self._game_speed = 1.0  # User-controlled speed multiplier (for HUD display)

    @property
    def time_elapsed(self) -> float:
        """float: The total elapsed game time in seconds."""
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        self._time_elapsed = value

    @property
    def scale(self) -> float:
        """float: Current time scale (game seconds per physics second)."""
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = max(0.1, min(value, 1000.0))  # Clamp to reasonable range

    @property
    def game_delta_multiplier(self) -> float:
        """float: Multiplier to convert physics dt to game dt."""
        return self._scale * self._game_speed

    def update(self, physics_dt: float) -> float:
        """
        Update game time based on physics delta.

        Args:
            physics_dt (float): The physics time delta.

        Returns:
            float: The game time delta.
        """
        game_dt = physics_dt * self.game_delta_multiplier
        self._time_elapsed += game_dt
        return game_dt

    @property
    def time_of_day(self) -> float:
        """
        Returns the time of day in hours (0.0 to 24.0).

        Returns:
            float: Time of day in hours.
        """
        return (self._time_elapsed % self.GAME_DAY_LENGTH) / 3600.0

    @property
    def hour_of_day(self) -> float:
        """
        Alias for time_of_day.

        Returns:
            float: Time of day in hours.
        """
        return self.time_of_day

    @property
    def is_night(self) -> bool:
        """
        Returns True if it is currently night time.

        Returns:
            bool: True if it is night.
        """
        t = self.time_of_day
        return t > self._night_start_hour or t < self._day_start_hour

    @property
    def day(self) -> int:
        """
        Returns the current day number (1-indexed).
        Day 1 starts at time_elapsed = 0.

        Returns:
            int: The current day number.
        """
        return int(self._time_elapsed / self.GAME_DAY_LENGTH) + 1

    @property
    def game_speed(self) -> float:
        """float: Current user-controlled game speed multiplier."""
        return self._game_speed

    @game_speed.setter
    def game_speed(self, value: float) -> None:
        self._game_speed = value
