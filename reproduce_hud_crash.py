
import pygame
import pygame_gui
from yukkuri_game.game.settings_service import SettingsService
from yukkuri_game.game.ui.hud_layout import HudLayout
from yukkuri_game.game.ui.hud_events import HudEvents

class MockGameManager:
    def __init__(self, world):
        self.world = world
        self.money = 1000
        self.save_game = lambda: print("Game saved")
        self.load_game = lambda: print("Game loaded")

class MockWorld:
    def __init__(self):
        self.services = MockServices()

class MockServices:
    def __init__(self):
        self.services = {}

    def try_get(self, service_type):
        return self.services.get(service_type)

    def register(self, service_type, instance):
        self.services[service_type] = instance

class MockEventBus:
    def publish(self, event):
        print(f"Event published: {event}")

def test_hud_save_settings():
    pygame.init()
    pygame.display.set_mode((800, 600))
    manager = pygame_gui.UIManager((800, 600))

    world = MockWorld()
    settings_service = SettingsService("test_hud_settings.json")
    world.services.register(SettingsService, settings_service)

    gm = MockGameManager(world)
    layout = HudLayout(manager, 800, 600)
    event_bus = MockEventBus()

    hud_events = HudEvents(layout, gm, event_bus)

    # Open settings window
    hud_events._open_settings()

    # Simulate save settings
    print("Saving settings from HUD...")
    hud_events._save_settings()
    print("Settings saved.")

if __name__ == "__main__":
    test_hud_save_settings()
