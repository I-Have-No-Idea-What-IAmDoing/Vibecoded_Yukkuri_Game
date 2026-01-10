from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components import LightSource, Transform, FloatingText
from yukkuri_game.game.renderer.pygame_backend import PygameBackend
from yukkuri_game.scenes.gameplay import GameplayScene
import os
import pygame


def test_headless_lighting_regression(game_driver: GameDriver, tmp_path):
    """
    Regression test: Validates that the lighting system works in headless mode.
    It sets up a scene with a RED light and White text.
    The screenshot should show that the text is illuminated (bright).
    Note: Exact color reproduction in headless/dummy driver + software blending
    can be tricky, so we verify illumination levels primarily.
    """
    screenshot_path = str(tmp_path / "test_lighting_regression.png")
    
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)

    game = driver.game
    world = driver.world

    # Center camera at (0,0) explicitly
    from yukkuri_game.game.camera import Camera

    camera = world.services.get(Camera)
    camera.camera_x = 0
    camera.camera_y = 0

    # 2. Add Light at (0,0)
    # Note: MouseLightSystem might exist (Entity 1, White, Intensity 0).
    light_ent = world.create_entity()
    world.add_component(
        light_ent,
        LightSource(
            radius=300,
            color=(255, 0, 0),  # Red
            intensity=2.0,
        ),
    )
    world.add_component(light_ent, Transform(x=0, y=0))

    # 3. Add Floating Text at (0,0) (White)
    text_ent = world.create_entity()
    world.add_component(
        text_ent,
        FloatingText(
            text="########",
            size=100,
            color=(255, 255, 255),
            lifetime=100.0,
            max_lifetime=100.0,
            velocity_y=0.0,
        ),
    )
    world.add_component(text_ent, Transform(x=0, y=0))

    # 4. Advance simulation to ensure SectorMap is updated
    driver.run_for(0.2)

    # 5. Take Screenshot
    driver.save_screenshot(screenshot_path)

    # 6. Verify Backend
    scene = game.scene_manager.current_scene
    assert scene.render_system.lights_enabled is True, "Lights should be enabled"
    assert isinstance(scene.render_system.renderer.backend, PygameBackend), (
        "Backend should be PygameBackend"
    )

    # 7. Verify Image Content
    assert os.path.exists(screenshot_path)
    img = pygame.image.load(screenshot_path)

    # We need to find where (0,0) world maps to screen.
    # By default, camera is centered on screen.
    # Screen center:
    center_x = game.width // 2
    center_y = game.height // 2

    # Check center pixels
    center_color = img.get_at((center_x, center_y))
    print(f"Center Pixel: {center_color}")

    # Verify it is bright enough (Lit)
    # Without lighting (just ambient 20,20,20), this would be very dark (< 30).
    # With lighting, it should be significantly brighter.
    is_lit = center_color.r > 100 or center_color.g > 100 or center_color.b > 100
    assert is_lit, f"Expected bright text (lit), got dark pixel {center_color}"

