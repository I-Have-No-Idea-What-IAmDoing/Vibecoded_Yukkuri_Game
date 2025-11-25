
import pytest
import math
from src.yukkuri_game.main import YukkuriGame
from src.yukkuri_game.testing.driver import GameDriver
from src.yukkuri_game.game.yukkuri_components import YukkuriStats

# Helper function to get a yukkuri's position
def get_yukkuri_pos(driver: GameDriver):
    yukkuris = driver.get_yukkuris()
    assert len(yukkuris) > 0
    return driver.get_transform(yukkuris[0]).x, driver.get_transform(yukkuris[0]).y

def test_navigation_straight_line(game_driver: GameDriver):
    """TC-NAV-1: Entity successfully navigates from A to B in an empty room."""
    # Setup
    driver = game_driver
    driver.setup()

    # Create a yukkuri and set a target
    start_pos = (100, 100)
    target_pos = (500, 100)
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    driver.set_ai_target_pos(yukkuri_id, *target_pos)

    # Run the simulation
    driver.run_for(seconds=10)

    # Verification
    final_pos = driver.get_transform(yukkuri_id)
    distance_to_target = math.hypot(final_pos.x - target_pos[0], final_pos.y - target_pos[1])
    assert distance_to_target < 20, f"Yukkuri did not reach target. Final pos: {final_pos}"

def test_navigation_with_obstacle(game_driver: GameDriver):
    """TC-NAV-2: Entity navigates around a simple, convex obstacle."""
    driver = game_driver
    driver.setup()

    start_pos = (100, 100)
    target_pos = (500, 100)
    obstacle_pos = (300, 100)

    # Create an obstacle
    driver.create_item("rock", *obstacle_pos)

    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    driver.set_ai_target_pos(yukkuri_id, *target_pos)

    path_length = 0
    last_pos = start_pos

    for _ in range(100): # 10 seconds at 10fps
        driver.run_for(seconds=0.1)
        current_pos = driver.get_transform(yukkuri_id)
        path_length += math.hypot(current_pos.x - last_pos[0], current_pos.y - last_pos[1])
        last_pos = (current_pos.x, current_pos.y)
        if math.hypot(current_pos.x - target_pos[0], current_pos.y - target_pos[1]) < 20:
            break

    final_pos = driver.get_transform(yukkuri_id)
    distance_to_target = math.hypot(final_pos.x - target_pos[0], final_pos.y - target_pos[1])

    assert distance_to_target < 20, f"Yukkuri did not reach target. Final pos: {final_pos}"
    assert path_length > 400, "Yukkuri did not navigate around the obstacle."

def test_stat_based_speed_modification(game_driver: GameDriver):
    """TC-NAV-4: Entity with low energy navigates slower."""
    driver = game_driver
    driver.setup()

    # Healthy yukkuri
    healthy_yukkuri = driver.create_yukkuri("reimu", 100, 100)
    driver.set_ai_target_pos(healthy_yukkuri, 500, 100)
    driver.run_for(seconds=3)
    healthy_pos = driver.get_transform(healthy_yukkuri)
    healthy_dist = math.hypot(healthy_pos.x - 100, healthy_pos.y - 100)

    # Reset and create a tired yukkuri
    driver.reset()
    driver.setup()

    tired_yukkuri = driver.create_yukkuri("reimu", 100, 100)
    stats = driver.world.get_component(tired_yukkuri, YukkuriStats)
    stats.energy = 20 # Low energy
    driver.set_ai_target_pos(tired_yukkuri, 500, 100)
    driver.run_for(seconds=3)
    tired_pos = driver.get_transform(tired_yukkuri)
    tired_dist = math.hypot(tired_pos.x - 100, tired_pos.y - 100)

    assert tired_dist < healthy_dist, "Low-energy yukkuri did not move slower."
