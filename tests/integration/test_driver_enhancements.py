from __future__ import annotations

"""Integration tests for testing infrastructure enhancements.

This module verifies the Behavior Tree node serialization, the fluent,
chainable EntityExpectation API, and the WarningDetector context manager.
"""

from typing import Any
from typing import Optional
import pytest
from unittest.mock import MagicMock
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.engine.components import Transform


class MockStatus:
    """Mock status class mimicking py_trees status enum."""

    def __init__(self, name: str) -> None:
        """Initializes MockStatus.

        Args:
            name (str): The name of the status.
        """
        self.name = name


class MockBehaviour:
    """Mock py_trees Behaviour node for formatting testing."""

    def __init__(
        self,
        name: str,
        status_name: str,
        children: list[MockBehaviour] | None = None,
        child: Optional[MockBehaviour] = None,
    ) -> None:
        """Initializes MockBehaviour.

        Args:
            name (str): The name of the behavior.
            status_name (str): The status name.
            children (list[MockBehaviour] | None): Nested children nodes.
            child (Optional[MockBehaviour]): Single child node for decorators.
        """
        self.name = name
        self.status = MockStatus(status_name)
        if children is not None:
            self.children = children
        if child is not None:
            self.child = child


def test_behavior_tree_formatting(game_driver: GameDriver) -> None:
    """Tests the recursive behavior tree formatting helper.

    Args:
        game_driver (GameDriver): The headless game driver fixture.
    """
    driver = game_driver

    # Construct mock BT: Sequence -> [Condition, Action]
    cond = MockBehaviour("IsHungry", "SUCCESS")
    act = MockBehaviour("Eat", "RUNNING")
    root = MockBehaviour("EatSequence", "RUNNING", children=[cond, act])

    formatted = driver._format_behavior_node(root)
    lines = formatted.strip().split("\n")

    assert len(lines) == 3
    assert "[-] EatSequence [RUNNING]" in lines[0]
    assert "  [-] IsHungry [SUCCESS]" in lines[1]
    assert "  [-] Eat [RUNNING]" in lines[2]


def test_behavior_tree_formatting_decorator(game_driver: GameDriver) -> None:
    """Tests BT formatting with wrapper/decorator nodes using child attribute.

    Args:
        game_driver (GameDriver): The headless game driver fixture.
    """
    driver = game_driver

    action = MockBehaviour("Wander", "SUCCESS")
    decorator = MockBehaviour("Inverter", "FAILURE", child=action)

    formatted = driver._format_behavior_node(decorator)
    lines = formatted.strip().split("\n")

    assert len(lines) == 2
    assert "[-] Inverter [FAILURE]" in lines[0]
    assert "  [-] Wander [SUCCESS]" in lines[1]


def test_fluent_expectations(game_driver: GameDriver) -> None:
    """Tests the fluent EntityExpectation API for assertion chaining.

    Args:
        game_driver (GameDriver): The headless game driver fixture.
    """
    driver = game_driver
    driver.setup()

    # Build reimu with custom builder
    reimu_id = (
        driver.yukkuri_builder("reimu")
        .at(100, 150)
        .with_stats(discipline=50.0, age=20.0, hunger=30.0)
        .build()
    )

    # 1. Test positive chain assertions
    (
        driver.expect_entity(reimu_id)
        .has_component(Transform)
        .has_position(100.0, 150.0, tolerance=2.0)
        .has_stat(discipline=50.0, age=20.0)
        .has_need(hunger=30.0)
        .has_emotion(happiness=0.0, stress=0.0)
        .has_attribute("discipline", 50.0)
        .has_attribute("hunger", 30.0)
        .is_performing_action("Idle")
    )

    # 2. Test failing component assertion
    class MockUnusedComponent:
        pass

    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_component(MockUnusedComponent)

    # 3. Test failing position assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_position(200.0, 200.0)

    # 4. Test failing stat assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_stat(discipline=10.0)

    # 5. Test failing need assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_need(hunger=99.0)

    # 6. Test failing emotion assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_emotion(stress=99.0)

    # 7. Test failing generic attribute assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).has_attribute("discipline", 99.0)

    # 8. Test failing action assertion
    with pytest.raises(AssertionError):
        driver.expect_entity(reimu_id).is_performing_action("Panic")


def test_warning_detector_missing_assets(game_driver: GameDriver) -> None:
    """Tests WarningDetector triggers assertions on missing assets.

    Args:
        game_driver (GameDriver): The headless game driver fixture.
    """
    driver = game_driver
    driver.setup()

    # Clear run logs
    driver._run_logs = []

    # 1. No warnings should pass safely
    with driver.check_warnings(fail_on_missing_assets=True):
        driver._run_logs.append("00:00:01 | INFO     | test — Ok log")

    # 2. Warning with Image not found should trigger AssertionError
    with pytest.raises(AssertionError) as exc_info:
        with driver.check_warnings(fail_on_missing_assets=True):
            driver._run_logs.append(
                "00:00:02 | WARNING  | rm — Image not found: dummy.png"
            )
    assert "Test triggered missing asset warnings:" in str(exc_info.value)
    assert "dummy.png" in str(exc_info.value)


def test_warning_detector_strict_no_warnings(game_driver: GameDriver) -> None:
    """Tests strict assert_no_warnings fails on standard warnings.

    Args:
        game_driver (GameDriver): The headless game driver fixture.
    """
    driver = game_driver
    driver.setup()

    # Clear run logs
    driver._run_logs = []

    # 1. Info logs should pass strict check
    with driver.check_warnings() as detector:
        driver._run_logs.append("00:00:01 | INFO     | test — Log")
        detector.assert_no_warnings()

    # 2. Standard warning should cause assert_no_warnings to fail
    with pytest.raises(AssertionError) as exc_info:
        with driver.check_warnings() as detector:
            driver._run_logs.append(
                "00:00:02 | WARNING  | test — Some standard warning"
            )
            detector.assert_no_warnings()
    assert "Test triggered warnings during strict check:" in str(exc_info.value)
    assert "Some standard warning" in str(exc_info.value)
