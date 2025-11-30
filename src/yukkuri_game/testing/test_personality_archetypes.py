"""
Tests for Personality Archetypes.
"""
import pytest
from ..game.yukkuri_components import Personality, PersonalityAxis

# This test ensures we can instantiate and use the 4-axis model
def test_personality_structure() -> None:
    """
    Tests that the Personality component correctly initializes the 4-axis structure.
    """
    p = Personality()
    assert isinstance(p.axis, PersonalityAxis)
    assert p.axis.kindness == 0
    assert p.axis.energy == 0
    assert p.axis.bravery == 0
    assert p.axis.greed == 0

def test_trait_shifts_concept() -> None:
    """
    Tests manual manipulation of the personality axis to simulate trait shifts.
    """
    # Verify we can manually apply shifts (logic is in trait_service usually, but here we test data structure support)
    p = Personality()
    p.axis.kindness = -50 # "Scum" trait shift

    assert p.axis.kindness == -50

    # Simulate drift back to center logic if we were to implement it here
    # (The proposal mentions "Natural resting point". The implementation in SocialSystem handles compatibility,
    # but the actual drift of personality *values* might be static or dynamic.
    # The code we have doesn't seem to dynamically drift the personality axis itself, which is fine,
    # as the proposal says Traits shift the "center". This means the value -50 IS the center.)
    pass
