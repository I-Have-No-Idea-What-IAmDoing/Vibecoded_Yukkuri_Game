"""
Constants for Yukkuri growth stages and scales.

These constants are shared between entity creation (prefabs) and preview rendering.
"""

# Growth stage age thresholds (in game seconds)
ADULT_AGE_THRESHOLD = 300.0
CHILD_AGE_THRESHOLD = 100.0

# Growth stage names
STAGE_BABY = "Baby"
STAGE_CHILD = "Child"
STAGE_ADULT = "Adult"

# Scale factors for each growth stage
SCALE_BABY = 0.5
SCALE_CHILD = 0.75
SCALE_ADULT = 1.0


def get_growth_stage_and_scale(age: float) -> tuple[str, float]:
    """
    Determines growth stage and scale based on age.

    Args:
        age (float): The age of the Yukkuri in game seconds.

    Returns:
        tuple[str, float]: The (growth_stage, scale) tuple.
    """
    if age >= ADULT_AGE_THRESHOLD:
        return STAGE_ADULT, SCALE_ADULT
    elif age >= CHILD_AGE_THRESHOLD:
        return STAGE_CHILD, SCALE_CHILD
    else:
        return STAGE_BABY, SCALE_BABY


def get_initial_scale() -> float:
    """
    Returns the scale for newly created Yukkuri (age=0, i.e., babies).

    Returns:
        float: The initial scale factor.
    """
    return SCALE_BABY
