
import pytest
from yukkuri_game.testing.predicates import WaitFrames, WaitUntil

def test_nested_generator_ignored(game_driver):
    """
    Demonstrates that yielding a generator object (forgetting 'yield from')
    currently results in the driver ignoring the step silently.
    """
    executed = False
    def sub_scenario():
        nonlocal executed
        executed = True
        yield WaitFrames(1)

    def main_scenario():
        # This yields a generator object, which the driver currently treats as "unknown" and ignores (pass)
        yield sub_scenario()

    # Proof of fix: the driver should now raise a TypeError
    with pytest.raises(TypeError, match="Did you forget to use 'yield from'"):
        game_driver.run_scenario(main_scenario())

def test_unknown_yield_ignored(game_driver):
    """
    Demonstrates that yielding an unknown object is ignored silently.
    """
    def main_scenario():
        yield "some_string_command" # Should probably be an error

    # Proof of fix: the driver should now raise a TypeError
    with pytest.raises(TypeError, match="Unknown scenario step"):
        game_driver.run_scenario(main_scenario())
