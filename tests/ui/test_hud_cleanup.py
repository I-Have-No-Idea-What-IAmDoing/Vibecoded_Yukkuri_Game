
import unittest
import sys
import os
import pygame
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, GamePausedEvent
from yukkuri_game.game.ui.hud import HUD
from yukkuri_game.engine.resource_manager import ResourceManager

class TestHudCleanup(unittest.TestCase):
    def setUp(self):
        # Setup pygame for UI Manager
        pygame.init()
        pygame.display.set_mode((800, 600), flags=pygame.HIDDEN)
        
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus, EventBus)
        
        # Mock ResourceManager needed by HUD
        rm = MagicMock()
        rm.yukkuri_types = {}
        rm.item_types = {}
        self.world.services.register(rm, ResourceManager)
        
        from pygame_gui import UIManager
        self.ui_manager = UIManager((800, 600))
        
        self.hud = HUD(self.ui_manager, self.world)

    def tearDown(self):
        pygame.quit()

    def test_listeners_registered(self):
        """Verify HUD registers listeners on init."""
        # Check internal subscribers dict of EventBus
        subscribers = self.event_bus._subscribers
        self.assertIn(EntitySelectedEvent, subscribers)
        self.assertIn(self.hud.on_entity_selected, subscribers[EntitySelectedEvent])
        self.assertIn(GamePausedEvent, subscribers)
        self.assertIn(self.hud.on_game_paused, subscribers[GamePausedEvent])

    def test_cleanup_removes_listeners(self):
        """Verify HUD.cleanup() removes listeners."""
        # Pre-check
        self.assertIn(self.hud.on_entity_selected, self.event_bus._subscribers[EntitySelectedEvent])
        
        # Call cleanup (not yet implemented, so this should fail or error if method missing)
        if hasattr(self.hud, "cleanup"):
            self.hud.cleanup()
            
            # Verify removal
            if EntitySelectedEvent in self.event_bus._subscribers:
                self.assertNotIn(self.hud.on_entity_selected, self.event_bus._subscribers[EntitySelectedEvent])
            
            if GamePausedEvent in self.event_bus._subscribers:
                self.assertNotIn(self.hud.on_game_paused, self.event_bus._subscribers[GamePausedEvent])
        else:
            self.fail("HUD does not have a cleanup method yet.")

if __name__ == "__main__":
    unittest.main()
