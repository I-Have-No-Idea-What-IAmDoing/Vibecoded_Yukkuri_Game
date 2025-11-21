
import pytest
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Sprite, Animation
from src.yukkuri_game.game.systems.animation import AnimationSystem

class TestAnimationSystem:
    def test_animation_update(self):
        world = World()
        system = AnimationSystem()

        # Create a sprite component with animation settings
        sprite = Sprite(
            image_name="test.png",
            width=32,
            height=32,
            frame_count=4,
            frame_duration=0.1,
            loop=True,
            is_animating=True
        )

        entity = world.create_entity()
        world.add_component(entity, sprite)

        # Initial state
        assert sprite.current_frame == 0
        assert sprite.timer == 0.0

        # Update 0.05s (less than duration)
        system.update(world, 0.05)
        assert sprite.current_frame == 0
        assert sprite.timer == 0.05

        # Update another 0.06s (total 0.11s -> should advance frame)
        system.update(world, 0.06)
        assert sprite.current_frame == 1
        assert sprite.timer == pytest.approx(0.01) # 0.11 - 0.10 = 0.01

        # Fast forward to end of animation
        system.update(world, 0.2) # +2 frames -> frame 3
        assert sprite.current_frame == 3

        system.update(world, 0.1) # +1 frame -> frame 4 -> loop to 0
        assert sprite.current_frame == 0

    def test_animation_switching(self):
        world = World()
        system = AnimationSystem()

        # Define animations
        idle_anim = Animation(name="idle", start_frame=0, frame_count=2, frame_duration=0.5, loop=True, row=0)
        walk_anim = Animation(name="walk", start_frame=0, frame_count=4, frame_duration=0.1, loop=True, row=1)

        sprite = Sprite(
            image_name="char.png",
            width=32,
            height=32,
            animations={"idle": idle_anim, "walk": walk_anim}
        )

        entity = world.create_entity()
        world.add_component(entity, sprite)

        # Set initial animation
        sprite.current_animation = "idle"

        # First update should apply the animation settings
        system.update(world, 0.0)

        assert sprite.frame_count == 2
        assert sprite.frame_duration == 0.5
        assert sprite.row == 0
        assert sprite.loop == True
        assert sprite._last_animation == "idle"

        # Advance time
        system.update(world, 0.6) # Should be frame 1 (0.6 > 0.5)
        assert sprite.current_frame == 1

        # Switch animation
        sprite.current_animation = "walk"

        # Next update should apply new settings and reset frame
        system.update(world, 0.05)

        assert sprite.frame_count == 4
        assert sprite.frame_duration == 0.1
        assert sprite.row == 1
        assert sprite.current_frame == 0 # Should reset
        assert sprite.timer == 0.05
        assert sprite._last_animation == "walk"

        # Update again to see if it progresses
        system.update(world, 0.06)
        assert sprite.current_frame == 1

    def test_start_frame_and_retrigger(self):
        world = World()
        system = AnimationSystem()

        # Define animations with start_frame and duplicate properties
        anim1 = Animation(name="anim1", start_frame=2, frame_count=2, frame_duration=0.1)
        anim2 = Animation(name="anim2", start_frame=4, frame_count=2, frame_duration=0.1)
        # same props as anim1 but different logical animation
        anim3 = Animation(name="anim3", start_frame=2, frame_count=2, frame_duration=0.1)

        sprite = Sprite(
            image_name="char.png",
            width=32,
            height=32,
            animations={"anim1": anim1, "anim2": anim2, "anim3": anim3}
        )
        entity = world.create_entity()
        world.add_component(entity, sprite)

        # Start anim1
        sprite.current_animation = "anim1"
        system.update(world, 0.15) # frame 1

        assert sprite.start_frame == 2
        assert sprite.current_frame == 1
        assert sprite._last_animation == "anim1"

        # Switch to anim3 (same properties)
        sprite.current_animation = "anim3"
        system.update(world, 0.0)

        # Should reset because name changed
        assert sprite.current_frame == 0
        assert sprite.start_frame == 2
        assert sprite._last_animation == "anim3"

        # Switch to anim2 (different start_frame)
        sprite.current_animation = "anim2"
        system.update(world, 0.0)

        assert sprite.start_frame == 4
        assert sprite.current_frame == 0
