import pytest
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.game.yukkuri_components import YukkuriStats


# Note: game_driver fixture comes from conftest.py

def test_image_comparison(game_driver: GameDriver, tmp_path):
    """
    Test image comparison feature.
    First we generate a reference image, then we compare against it.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)

    # Setup a stable scene
    driver.reload_scene(GameplayScene)
    driver.seed_rng(12345)  # Force seed for rendering determinism

    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(1.0)  # Let it settle

    reference_path = str(tmp_path / "reference.png")
    driver.save_screenshot(reference_path)

    # Run again with same seed
    driver.reload_scene(GameplayScene)
    driver.seed_rng(12345)

    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(1.0)

    test_path = str(tmp_path / "test.png")

    # Should match exactly or very closely
    assert driver.compare_screenshot(test_path, reference_path, tolerance=0.01)


def test_image_comparison_failure(game_driver: GameDriver, tmp_path):
    """
    Test that image comparison fails when scenes are different.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)

    # Setup Scene A
    driver.reload_scene(GameplayScene)
    driver.seed_rng(12345)
    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(0.5)

    reference_path = str(tmp_path / "ref_fail.png")
    driver.save_screenshot(reference_path)

    # Setup Scene B (Different position)
    driver.reload_scene(GameplayScene)
    driver.seed_rng(12345)
    # We want a significant difference.
    # The previous diff ratio was ~0.006 (0.6%) which is < 1% tolerance, so it passed comparison (which means test failed).
    # We need diff > 1%.
    # Let's spawn many entities in different spots.

    for i in range(50):
        driver.create_yukkuri("reimu", 100 + i * 10, 100 + i * 10)

    driver.run_for(0.5)

    test_path = str(tmp_path / "test_fail.png")

    # Should fail comparison (return False)
    assert not driver.compare_screenshot(test_path, reference_path, tolerance=0.01)


def test_state_dump_on_failure(game_driver: GameDriver):
    """
    Verify that state dump works.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)
    driver.create_yukkuri("reimu", 100, 100)
    driver.run_for(0.1)

    dump = driver.dump_state()
    assert "Simulated Time:" in dump
    assert "Frame Count:" in dump
    assert "Entities:" in dump
    # Entity ID might be just a number
    assert "Entity" in dump


def test_reset_consistency(game_driver: GameDriver):
    """
    Verify that reset clears everything properly.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)
    driver.create_yukkuri("reimu", 100, 100)

    assert (
        len(driver.get_entities_with(YukkuriStats)) >= 1
    )  # 1 + potentially initial one

    driver.reset()

    assert driver.simulated_time == 0.0
    assert driver.frame_count == 0
    # World should be empty
    assert len(driver.world.get_all_entities()) == 0

    # To properly "reset" for a new test case within same app instance:
    driver.reload_scene(GameplayScene)

    driver.wait_until_scene(GameplayScene)

    # If headless, we manually spawn.
    if driver.game.headless:
        driver.create_yukkuri("reimu", 100, 100)

    assert len(driver.get_entities_with(YukkuriStats)) >= 1
