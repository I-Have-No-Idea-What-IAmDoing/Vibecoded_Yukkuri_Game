import pytest
import os
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.engine.application import Application
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.game.yukkuri_components import YukkuriStats


@pytest.fixture
def headless_app():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    app = Application(headless=True)
    yield app
    app.quit()


@pytest.fixture
def driver(headless_app):
    driver = GameDriver(headless_app)
    driver.setup()
    return driver


def test_image_comparison(driver, tmp_path):
    """
    Test image comparison feature.
    First we generate a reference image, then we compare against it.
    """
    driver.wait_until_scene(GameplayScene)

    # Setup a stable scene
    driver.reset()
    # We must explicitly pop scene to allow re-setup cleanly if we want full isolation
    # driver.reset() clears entities, but scene persists.
    # driver.setup() is idempotent if scene exists.
    # So if we want to ensure same starting conditions, clearing entities is fine,
    # provided we also ensure services/systems are clean.

    # For image comparison, let's be sure.
    driver.game.scene_manager.pop()
    driver.setup()
    driver.seed_rng(12345)  # Force seed for rendering determinism

    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(1.0)  # Let it settle

    reference_path = str(tmp_path / "reference.png")
    driver.save_screenshot(reference_path)

    # Run again with same seed
    driver.reset()
    driver.game.scene_manager.pop()
    driver.setup()
    driver.seed_rng(12345)

    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(1.0)

    test_path = str(tmp_path / "test.png")

    # Should match exactly or very closely
    assert driver.compare_screenshot(test_path, reference_path, tolerance=0.01)


def test_image_comparison_failure(driver, tmp_path):
    """
    Test that image comparison fails when scenes are different.
    """
    driver.wait_until_scene(GameplayScene)

    # Setup Scene A
    driver.reset()
    driver.game.scene_manager.pop()
    driver.setup()
    driver.seed_rng(12345)
    driver.create_yukkuri("reimu", 400, 300)
    driver.run_for(0.5)

    reference_path = str(tmp_path / "ref_fail.png")
    driver.save_screenshot(reference_path)

    # Setup Scene B (Different position)
    driver.reset()
    driver.game.scene_manager.pop()
    driver.setup()
    driver.seed_rng(12345)
    # We want a significant difference.
    # The previous diff ratio was ~0.006 (0.6%) which is < 1% tolerance, so it passed comparison (which means test failed).
    # We need diff > 1%.
    # Let's spawn many entities in different spots.

    for i in range(20):
        driver.create_yukkuri("reimu", 100 + i * 30, 100 + i * 20)

    driver.run_for(0.5)

    test_path = str(tmp_path / "test_fail.png")

    # Should fail comparison (return False)
    assert not driver.compare_screenshot(test_path, reference_path, tolerance=0.01)


def test_state_dump_on_failure(driver):
    """
    Verify that state dump works.
    """
    driver.wait_until_scene(GameplayScene)
    driver.create_yukkuri("reimu", 100, 100)
    driver.run_for(0.1)

    dump = driver.dump_state()
    assert "Simulated Time:" in dump
    assert "Frame Count:" in dump
    assert "Entities:" in dump
    # Entity ID might be just a number
    assert "Entity" in dump


def test_reset_consistency(driver):
    """
    Verify that reset clears everything properly.
    """
    driver.wait_until_scene(GameplayScene)
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
    # We should probably clear scene and re-push.

    driver.game.scene_manager.pop()
    driver.setup()

    driver.wait_until_scene(GameplayScene)

    # If headless, we manually spawn.
    if driver.game.headless:
        driver.create_yukkuri("reimu", 100, 100)

    assert len(driver.get_entities_with(YukkuriStats)) >= 1
