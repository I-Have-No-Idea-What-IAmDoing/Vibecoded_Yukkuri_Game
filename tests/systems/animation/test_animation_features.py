import unittest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.data_models import AnimationDefinition
from yukkuri_game.engine.components import Sprite, Animator
from yukkuri_game.game.systems.animation import AnimationSystem
from yukkuri_game.game.events import AnimationEvent


class TestAnimationFeatures(unittest.TestCase):
    def setUp(self):
        from test_utils import make_configured_world
        self.world = make_configured_world()
        self.event_bus = self.world.services.get(EventBus)
        self.system = AnimationSystem()
        self.world.add_system(self.system)

        # Mock Event Handler
        self.event_handler = MagicMock()
        self.event_bus.subscribe(AnimationEvent, self.event_handler)

    def test_speed_multiplier(self) -> None:
        """Test that speed multiplier affects animation timing."""
        anim_def = AnimationDefinition(
            name="walk", frames=[0, 1, 2], frame_duration=1.0, loop=True
        )

        animator = Animator(
            animations={"walk": anim_def},
            current_animation="walk",
            speed=2.0,  # Double speed
        )
        sprite = Sprite(image_name="test.png", width=32, height=32)

        entity = self.world.create_entity()
        self.world.add_component(entity, animator)
        self.world.add_component(entity, sprite)

        # Update with 0.6s (effective 1.2s)
        self.system.update(self.world, 0.6)

        # Should have advanced 1 frame (1.2s > 1.0s)
        self.assertEqual(animator.current_frame_index, 1)
        self.assertEqual(sprite.current_frame, 1)

    def test_ping_pong_loop(self) -> None:
        """Test ping-pong looping behavior."""
        anim_def = AnimationDefinition(
            name="sway", frames=[0, 1, 2], frame_duration=0.1, loop=True, ping_pong=True
        )

        animator = Animator(animations={"sway": anim_def}, current_animation="sway")
        sprite = Sprite(image_name="test.png", width=32, height=32)

        entity = self.world.create_entity()
        self.world.add_component(entity, animator)
        self.world.add_component(entity, sprite)

        # Frame 0 -> 1
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 1)
        self.assertTrue(animator.forward)

        # Frame 1 -> 2
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 2)
        self.assertTrue(
            animator.forward
        )  # Still technically forward until it tries to go past

        # Frame 2 -> 1 (Bounce back)
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 1)
        self.assertFalse(animator.forward)

        # Frame 1 -> 0
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 0)
        self.assertFalse(animator.forward)

        # Frame 0 -> 1 (Bounce forward)
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 1)
        self.assertTrue(animator.forward)

    def test_animation_events(self) -> None:
        """Test that events are triggered at specific frames."""
        anim_def = AnimationDefinition(
            name="attack",
            frames=[0, 1, 2],
            frame_duration=0.1,
            loop=False,
            events={1: "hit"},  # Event at frame index 1
        )

        animator = Animator(animations={"attack": anim_def}, current_animation="attack")
        sprite = Sprite(image_name="test.png", width=32, height=32)

        entity = self.world.create_entity()
        self.world.add_component(entity, animator)
        self.world.add_component(entity, sprite)

        # 0 -> 1 triggers event
        self.system.update(self.world, 0.1)  # Frame 0 to 1 (requires >= 0.1s)

        self.assertEqual(animator.current_frame_index, 1)
        self.event_handler.assert_called_once()

        event = self.event_handler.call_args[0][0]
        self.assertIsInstance(event, AnimationEvent)
        self.assertEqual(event.event_type, "hit")
        self.assertEqual(event.frame_index, 1)

    def test_auto_transition(self) -> None:
        """Test automatic transition to next animation."""
        idle_def = AnimationDefinition(
            name="idle", frames=[0], frame_duration=1.0, loop=True
        )
        attack_def = AnimationDefinition(
            name="attack", frames=[0, 1], frame_duration=0.1, loop=False
        )

        animator = Animator(
            animations={"idle": idle_def, "attack": attack_def},
            current_animation="attack",
            next_animation="idle",
        )
        sprite = Sprite(image_name="test.png", width=32, height=32)

        entity = self.world.create_entity()
        self.world.add_component(entity, animator)
        self.world.add_component(entity, sprite)

        # Frame 0 -> 1
        self.system.update(self.world, 0.1)
        self.assertEqual(animator.current_frame_index, 1)
        self.assertFalse(animator.finished)
        self.assertEqual(animator.current_animation, "attack")

        # Frame 1 -> Finish -> Switch
        self.system.update(self.world, 0.1)

        # Should have switched to idle
        self.assertEqual(animator.current_animation, "idle")
        self.assertEqual(animator.current_frame_index, 0)
        self.assertFalse(animator.finished)


if __name__ == "__main__":
    unittest.main()
