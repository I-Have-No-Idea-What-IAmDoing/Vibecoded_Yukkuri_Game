from typing import Dict, Any

class Need:
    def __init__(self, name: str, min_val: float, max_val: float, initial_val: float, decay_per_min: float) -> None:
        self.name: str = name
        self.min: float = min_val
        self.max: float = max_val
        self.value: float = initial_val
        self.decay_rate: float = decay_per_min / 60.0  # Convert to decay per second

    def update(self, delta_time: float) -> None:
        """Decays the need over time."""
        if self.decay_rate > 0:
            self.value -= self.decay_rate * delta_time
            if self.value < self.min:
                self.value = self.min

    def add(self, amount: float) -> None:
        """Increases the need's value."""
        self.value += amount
        if self.value > self.max:
            self.value = self.max

    def __repr__(self) -> str:
        return f"{self.name}: {self.value:.2f}"
