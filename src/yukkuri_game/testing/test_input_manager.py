import unittest

# Use real pygame if available (uv should provide it)
import pygame

from ..engine.input_manager import InputManager, InputContext


class TestInputManager(unittest.TestCase):
    def setUp(self) -> None:
        self.input_manager = InputManager()

    def test_initialization(self) -> None:
        self.assertIn(InputContext.MENU, self.input_manager._active_contexts)

    def test_context_switching(self) -> None:
        self.input_manager.switch_context(InputContext.GAMEPLAY)
        self.assertIn(InputContext.GAMEPLAY, self.input_manager._active_contexts)
        self.assertNotIn(InputContext.MENU, self.input_manager._active_contexts)

        self.input_manager.set_context(InputContext.MENU, active=True)
        self.assertIn(InputContext.GAMEPLAY, self.input_manager._active_contexts)
        self.assertIn(InputContext.MENU, self.input_manager._active_contexts)

    def test_input_consumption(self) -> None:
        # Menu has higher priority (10) than Gameplay (1)
        self.input_manager._active_contexts = {InputContext.MENU, InputContext.GAMEPLAY}

        K_UP = pygame.K_UP

        # Verify mapping exists
        # MENU: up -> K_UP
        # GAMEPLAY: up -> K_UP

        # Check if GAMEPLAY "up" is consumed by MENU
        is_consumed = self.input_manager._is_consumed_by_higher_priority(
            K_UP, InputContext.GAMEPLAY, is_mouse=False
        )
        self.assertTrue(is_consumed, "K_UP should be consumed by MENU context")

        # Check if MENU "up" is consumed (should be False as no higher context)
        is_consumed = self.input_manager._is_consumed_by_higher_priority(
            K_UP, InputContext.MENU, is_mouse=False
        )
        self.assertFalse(is_consumed, "K_UP should NOT be consumed for MENU context")
