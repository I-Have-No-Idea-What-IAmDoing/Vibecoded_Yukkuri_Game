import math
import pytest
from src.yukkuri_game.game.ai.steering import Steering

def test_limit_magnitude():
    # Test vector within limit
    vec = (5.0, 0.0)
    max_val = 10.0
    result = Steering._limit_magnitude(vec, max_val)
    assert result == vec

    # Test vector exceeding limit
    vec = (20.0, 0.0)
    max_val = 10.0
    result = Steering._limit_magnitude(vec, max_val)
    assert math.isclose(result[0], 10.0)
    assert math.isclose(result[1], 0.0)

    # Test zero vector
    vec = (0.0, 0.0)
    result = Steering._limit_magnitude(vec, max_val)
    assert result == (0.0, 0.0)

def test_seek():
    position = (0.0, 0.0)
    target = (100.0, 0.0)
    max_speed = 10.0
    velocity = (0.0, 0.0)

    # Seek directly to the right
    result = Steering.seek(position, target, max_speed, velocity)
    # Desired velocity is (10, 0). Steering is (10, 0) - (0, 0) = (10, 0).
    # New velocity is (0, 0) + (10, 0) = (10, 0).
    assert math.isclose(result[0], 10.0)
    assert math.isclose(result[1], 0.0)

    # Already at target
    result = Steering.seek(target, target, max_speed, velocity)
    assert result == (0.0, 0.0)

    # Test max force
    velocity = (10.0, 0.0)
    target = (0.0, 100.0) # Seek up
    # Desired (0, 10).
    # Steer (0, 10) - (10, 0) = (-10, 10). Mag ~14.14.
    # Max force 5.0 (arbitrary small).
    max_force = 5.0
    result = Steering.seek(position, target, max_speed, velocity, max_force=max_force)

    # Steer should be limited to 5.
    # Steer direction is (-1, 1) normalized.
    # Steer vector ~ (-3.53, 3.53)
    # New Vel = (10, 0) + (-3.53, 3.53) = (6.47, 3.53)
    # Limit new vel to max_speed (10).
    assert result[0] > 0 # Still moving somewhat right
    assert result[1] > 0 # Turning up

def test_arrive():
    position = (0.0, 0.0)
    target = (100.0, 0.0)
    max_speed = 10.0
    slowing_radius = 50.0

    # Far away (outside slowing radius)
    # Should return max speed towards target
    result = Steering.arrive(position, target, max_speed, slowing_radius)
    assert math.isclose(result[0], 10.0)
    assert math.isclose(result[1], 0.0)

    # Inside slowing radius
    position = (90.0, 0.0) # Dist 10
    result = Steering.arrive(position, target, max_speed, slowing_radius)
    # Speed should be 10 * (10/50) = 2.0
    assert math.isclose(result[0], 2.0)
    assert math.isclose(result[1], 0.0)

    # At target
    position = (100.0, 0.0)
    result = Steering.arrive(position, target, max_speed, slowing_radius)
    assert result == (0.0, 0.0)

def test_wander():
    velocity = (10.0, 0.0)
    max_speed = 10.0

    # Stationary wander
    result = Steering.wander((0.0, 0.0), max_speed)
    mag = math.hypot(result[0], result[1])
    assert math.isclose(mag, max_speed)

    # Moving wander
    result = Steering.wander(velocity, max_speed)
    mag = math.hypot(result[0], result[1])
    assert math.isclose(mag, max_speed)

    # Since it's random, we just check magnitude and that it returns valid values
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)
