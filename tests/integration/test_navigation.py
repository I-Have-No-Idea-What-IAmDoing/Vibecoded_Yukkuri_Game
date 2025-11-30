
import pytest
import math
from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.yukkuri_components import YukkuriStats

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

    # Create a yukkuri and a target item
    start_pos = (100, 100)
    target_pos = (500, 100)
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    item_id = driver.create_item("cookie", *target_pos)

    # Set AI to Eat the item
    driver.set_ai_action(yukkuri_id, "Eat", target_id=item_id)

    # Run the simulation
    driver.run_for(seconds=10)

    # Verification
    final_pos = driver.get_transform(yukkuri_id)
    distance_to_target = math.hypot(final_pos.x - target_pos[0], final_pos.y - target_pos[1])
    # The Eat action consumes the item when close.
    # The yukkuri might stop when item is consumed.
    # Distance checks should be < 30 (Interact range).
    assert distance_to_target < 35, f"Yukkuri did not reach target. Final pos: {final_pos}"

def test_navigation_with_obstacle(game_driver: GameDriver):
    """TC-NAV-2: Entity navigates around a simple, convex obstacle."""
    driver = game_driver
    driver.setup()

    start_pos = (100, 100)
    target_pos = (500, 100)
    obstacle_pos = (300, 100)

    # Create an obstacle (bed is static, physics enabled)
    item_id = driver.create_item("bed", *obstacle_pos)
    # Make it static so it acts as an obstacle
    from yukkuri_game.game.components import PhysicsBody
    import pymunk
    phys = driver.world.get_component(item_id, PhysicsBody)
    if phys:
        phys.body.body_type = pymunk.Body.STATIC
        # Force reindex shape
        phys.body.space.reindex_shapes_for_body(phys.body)

        # Also update navigation grid so pathfinding sees it
        from yukkuri_game.game.ai.navigation_service import NavigationService
        nav = driver.world.services.try_get(NavigationService)
        if nav:
            # Bed size is 64x64. Update grid cells.
            # Simplified: Block center
            nav.update_obstacle(obstacle_pos[0], obstacle_pos[1], False)
            # Block surrounding area approx 64x64
            for dx in [-20, 0, 20]:
                for dy in [-20, 0, 20]:
                    nav.update_obstacle(obstacle_pos[0]+dx, obstacle_pos[1]+dy, False)

    # Create yukkuri and target item
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    item_id = driver.create_item("cookie", *target_pos)

    driver.set_ai_action(yukkuri_id, "Eat", target_id=item_id)

    path_length = 0
    last_pos = start_pos

    for _ in range(100): # 10 seconds at 10fps
        driver.run_for(seconds=0.1)
        current_pos = driver.get_transform(yukkuri_id)
        path_length += math.hypot(current_pos.x - last_pos[0], current_pos.y - last_pos[1])
        last_pos = (current_pos.x, current_pos.y)
        if math.hypot(current_pos.x - target_pos[0], current_pos.y - target_pos[1]) < 35:
            break

    final_pos = driver.get_transform(yukkuri_id)
    distance_to_target = math.hypot(final_pos.x - target_pos[0], final_pos.y - target_pos[1])

    assert distance_to_target < 35, f"Yukkuri did not reach target. Final pos: {final_pos}"
    assert path_length > 400, "Yukkuri did not navigate around the obstacle."

def test_stat_based_speed_modification(game_driver: GameDriver):
    """TC-NAV-4: Entity with low energy navigates slower."""
    driver = game_driver
    driver.setup()

    # Healthy yukkuri
    healthy_yukkuri = driver.create_yukkuri("reimu", 100, 100)
    item1 = driver.create_item("cookie", 500, 100)
    driver.set_ai_action(healthy_yukkuri, "Eat", target_id=item1)

    driver.run_for(seconds=3)
    healthy_pos = driver.get_transform(healthy_yukkuri)
    healthy_dist = math.hypot(healthy_pos.x - 100, healthy_pos.y - 100)

    # Reset and create a tired yukkuri
    driver.reset()
    driver.setup()

    tired_yukkuri = driver.create_yukkuri("reimu", 100, 100)
    stats = driver.world.get_component(tired_yukkuri, YukkuriStats)
    if stats:
        stats.energy = 20 # Low energy

    item2 = driver.create_item("cookie", 500, 100)
    driver.set_ai_action(tired_yukkuri, "Eat", target_id=item2)

    driver.run_for(seconds=3)
    tired_pos = driver.get_transform(tired_yukkuri)
    tired_dist = math.hypot(tired_pos.x - 100, tired_pos.y - 100)

    assert tired_dist < healthy_dist, "Low-energy yukkuri did not move slower."
