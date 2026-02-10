import math
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components import SteeringComponent
from yukkuri_game.game.services import TimeService
from yukkuri_game.game.ai.navigation_constants import TraversalCapability


# Helper function to get a yukkuri's position
def get_yukkuri_pos(driver: GameDriver):
    yukkuris = driver.get_yukkuris()
    assert len(yukkuris) > 0
    return driver.get_transform(yukkuris[0]).x, driver.get_transform(yukkuris[0]).y


def _set_daytime(driver: GameDriver, hour: float = 8.0) -> None:
    time_service = driver.world.services.try_get(TimeService)
    if time_service:
        time_service.time_elapsed = hour * 3600.0


def _run_until_near_target(
    driver: GameDriver,
    entity_id: int,
    target_pos: tuple[float, float],
    threshold: float = 35.0,
    max_seconds: float = 5.0,
    track_path_length: bool = False,
) -> tuple[float, float]:
    """
    Run simulation until entity is near target or max_seconds elapsed.
    Returns (final_distance, path_length).
    Much faster than fixed-duration loops.
    """
    target_time = driver.simulated_time + max_seconds
    path_length = 0.0
    last_pos = None

    if track_path_length:
        transform = driver.get_transform(entity_id)
        last_pos = (transform.x, transform.y)

    while driver.simulated_time < target_time:
        driver._tick()
        transform = driver.get_transform(entity_id)
        current_pos = (transform.x, transform.y)

        if track_path_length and last_pos:
            path_length += math.hypot(
                current_pos[0] - last_pos[0], current_pos[1] - last_pos[1]
            )
            last_pos = current_pos

        distance = math.hypot(
            current_pos[0] - target_pos[0], current_pos[1] - target_pos[1]
        )
        if distance < threshold:
            break

    final_transform = driver.get_transform(entity_id)
    final_distance = math.hypot(
        final_transform.x - target_pos[0], final_transform.y - target_pos[1]
    )
    return final_distance, path_length


def test_navigation_straight_line(game_driver: GameDriver):
    """TC-NAV-1: Entity successfully navigates from A to B in an empty room."""
    driver = game_driver
    driver.setup()
    _set_daytime(driver)

    # Create a yukkuri and a target item
    start_pos = (100, 100)
    target_pos = (500, 100)
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    item_id = driver.create_item("cookie", *target_pos)

    # Set AI to Eat the item
    driver.set_ai_action(yukkuri_id, "Eat", target_id=item_id)

    # Run until near target (early exit optimization)
    # Threshold 75.0 accounts for body radius (32) + item radius (16) + margin
    distance_to_target, _ = _run_until_near_target(
        driver, yukkuri_id, target_pos, threshold=75.0, max_seconds=5.0
    )

    # The Eat action consumes the item when close.
    assert distance_to_target < 75.0, (
        f"Yukkuri did not reach target. Distance: {distance_to_target}"
    )


def test_navigation_with_obstacle(game_driver: GameDriver):
    """TC-NAV-2: Entity navigates around a simple, convex obstacle."""
    driver = game_driver
    driver.setup()
    _set_daytime(driver)

    start_pos = (100, 100)
    target_pos = (500, 100)
    obstacle_pos = (300, 100)

    # Create an obstacle (bed is static, physics enabled)
    obstacle_id = driver.create_item("bed", *obstacle_pos)
    # Make it static so it acts as an obstacle
    from yukkuri_game.game.components import PhysicsBody
    import pymunk

    from yukkuri_game.game.ai.navigation_service import NavigationService, ObstacleType

    nav = driver.world.services.try_get(NavigationService)

    phys = driver.world.get_component(obstacle_id, PhysicsBody)
    if phys:
        phys.body.body_type = pymunk.Body.STATIC
        # Force reindex shape
        phys.body.space.reindex_shapes_for_body(phys.body)

        # Also update navigation grid so pathfinding sees it
        if nav:
            # Bed size is 64x64. Block the rectangular area.
            nav.update_obstacle_rect(
                obstacle_pos[0],
                obstacle_pos[1],
                64,
                64,
                walkable=False,
                obstacle_type=ObstacleType.HIGH
            )

    # Validate pathfinding detours around the obstacle
    assert nav is not None, "NavigationService not available"

    path = nav.find_path(start_pos, target_pos, capabilities=TraversalCapability.WALK)
    assert path, "Pathfinding failed to return a path."

    # Obstacle bounds: centered at (300, 100), size 64x64
    min_x, max_x = obstacle_pos[0] - 32, obstacle_pos[0] + 32
    min_y, max_y = obstacle_pos[1] - 32, obstacle_pos[1] + 32

    # Path should not pass through the obstacle
    for x, y in path:
        if min_x <= x <= max_x and min_y <= y <= max_y:
            raise AssertionError(f"Path collision detected at {(x, y)} inside obstacle")

    # Ensure detour: path should deviate beyond obstacle's vertical span
    path_min_y = min(p[1] for p in path)
    path_max_y = max(p[1] for p in path)
    assert path_min_y < min_y or path_max_y > max_y, (
        f"Path did not detour around obstacle. Y-Range: {path_min_y}-{path_max_y}"
    )


def test_stat_based_speed_modification(game_driver: GameDriver):
    """TC-NAV-4: Entity with modified max_speed navigates slower."""
    driver = game_driver
    driver.setup()
    _set_daytime(driver)

    # Create both yukkuris simultaneously in the same world
    # Place them in separate lanes to avoid collision
    fast_yukkuri = driver.create_yukkuri("reimu", 100, 100)
    slow_yukkuri = driver.create_yukkuri("reimu", 100, 200)

    # Directly modify max_speed on the SteeringComponent (reliable way)
    steering = driver.world.get_component(slow_yukkuri, SteeringComponent)
    if steering:
        steering.max_speed = 50.0  # Default is 150.0

    # Create separate targets for each yukkuri
    item1 = driver.create_item("cookie", 500, 100)
    item2 = driver.create_item("cookie", 500, 200)

    driver.set_ai_action(fast_yukkuri, "Eat", target_id=item1)
    driver.set_ai_action(slow_yukkuri, "Eat", target_id=item2)

    # Run simulation once (saves ~50% time vs running twice)
    driver.run_for(seconds=3)

    fast_pos = driver.get_transform(fast_yukkuri)
    slow_pos = driver.get_transform(slow_yukkuri)

    fast_dist = math.hypot(fast_pos.x - 100, fast_pos.y - 100)
    slow_dist = math.hypot(slow_pos.x - 100, slow_pos.y - 200)

    assert slow_dist < fast_dist, (
        f"Slow yukkuri did not navigate slower. Fast: {fast_dist}, Slow: {slow_dist}"
    )
