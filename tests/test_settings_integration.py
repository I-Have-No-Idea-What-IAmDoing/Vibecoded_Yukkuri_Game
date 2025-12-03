"""
Tests for Settings integration (Service, UI, Audio, Display).
"""
import unittest
import os
import json
import copy
import pygame
import pygame_gui
from unittest.mock import MagicMock, patch, mock_open
from yukkuri_game.game.settings_service import SettingsService
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.ui.hud_events import HudEvents
from yukkuri_game.game.ui.hud_layout import HudLayout
from yukkuri_game.game.events import ResolutionChangedEvent

class TestSettingsIntegration(unittest.TestCase):
    """
    Tests the interaction between SettingsService, AudioManager, and HUD UI.
    """
    def setUp(self) -> None:
        """
        Sets up mocks and services for testing.
        """
        # Mock pygame and pygame_gui
        self.mock_pygame_display = patch('pygame.display').start()
        self.mock_pygame_mixer = patch('pygame.mixer').start()

        # Setup SettingsService with a test file
        self.test_settings_file = "test_settings.toml"
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)

        self.resource_manager = ResourceManager(data_dir=".")
        self.settings_service = SettingsService(self.resource_manager, self.test_settings_file)

        # Setup AudioManager
        self.audio_manager = AudioManager()
        # Force enable for testing interactions, though mocking mixer helps
        self.audio_manager.enabled = True

        # Setup mocks for HudEvents
        self.layout = MagicMock(spec=HudLayout)
        self.gm = MagicMock()
        self.event_bus = MagicMock()

        # Mock Service Locator in GM
        self.gm.world.services.try_get.side_effect = self._service_locator

        self.hud_events = HudEvents(self.layout, self.gm, self.event_bus)

        # Manually inject services since HudEvents tries to get them in init
        self.hud_events.settings_service = self.settings_service
        self.hud_events.audio_manager = self.audio_manager

        # Mock layout controls
        self.layout.settings_controls = {}
        self.layout.settings_window = MagicMock()

        # Setup common buttons on layout
        self.layout.save_btn = MagicMock()
        self.layout.load_btn = MagicMock()
        self.layout.pause_btn = MagicMock()
        self.layout.speed_btn = MagicMock()
        self.layout.settings_btn = MagicMock()
        self.layout.clean_btn = MagicMock()
        self.layout.buy_buttons = {}

    def tearDown(self) -> None:
        """
        Cleans up mocks and temporary files.
        """
        patch.stopall()
        if os.path.exists(self.test_settings_file):
            os.remove(self.test_settings_file)

    def _service_locator(self, service_type):
        if service_type == SettingsService:
            return self.settings_service
        if service_type == AudioManager:
            return self.audio_manager
        return None

    def test_settings_service_load_save(self) -> None:
        """
        Tests loading and saving settings to a file.
        """
        # Re-init service with fresh defaults
        self.settings_service = SettingsService(self.resource_manager, self.test_settings_file)

        self.assertEqual(self.settings_service.get("audio", "master_volume"), 0.5)

        # Change settings
        self.settings_service.set("audio", "master_volume", 0.8)
        self.settings_service.save_settings()

        # Verify file creation
        self.assertTrue(os.path.exists(self.test_settings_file))

        # Reload
        new_service = SettingsService(self.resource_manager, self.test_settings_file)
        self.assertEqual(new_service.get("audio", "master_volume"), 0.8)

    def test_audio_manager_volume_control(self) -> None:
        """
        Tests that AudioManager correctly sets volumes on pygame.mixer.
        """
        self.audio_manager.set_master_volume(0.5)
        self.assertEqual(self.audio_manager.master_volume, 0.5)

        self.audio_manager.set_bgm_volume(0.7)
        self.assertEqual(self.audio_manager.bgm_volume, 0.7)

        self.audio_manager.set_sfx_volume(0.3)
        self.assertEqual(self.audio_manager.sfx_volume, 0.3)

        # Verify mixer calls (mocked)
        # music volume = master * bgm = 0.5 * 0.7 = 0.35
        # Note: AudioManager calls music.set_volume in _update_all_volumes
        # We need to ensure logic is correct

        # Check if set_bgm_volume calls music set volume
        # It does: pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)
        # However, we mocked pygame.mixer, so let's check the mock
        self.assertTrue(self.mock_pygame_mixer.music.set_volume.called)

        # The exact call value depends on float precision, so we might just check it was called.
        # But we can check args
        args, _ = self.mock_pygame_mixer.music.set_volume.call_args
        self.assertAlmostEqual(args[0], 0.35)

    def test_hud_slider_update(self) -> None:
        """
        Tests that HUD slider events update audio manager.
        """
        # Setup slider event
        slider = MagicMock()
        self.layout.settings_controls["master_slider"] = slider

        event = MagicMock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_HORIZONTAL_SLIDER_MOVED
        event.ui_element = slider
        event.value = 75 # 0-100 range

        # Process event
        handled = self.hud_events.process_event(event)

        self.assertTrue(handled)
        self.assertEqual(self.audio_manager.master_volume, 0.75)

    def test_hud_save_settings(self) -> None:
        """
        Tests saving settings from the HUD UI.
        """
        # Setup UI controls
        master_slider = MagicMock()
        master_slider.get_current_value.return_value = 80

        bgm_slider = MagicMock()
        bgm_slider.get_current_value.return_value = 60

        sfx_slider = MagicMock()
        sfx_slider.get_current_value.return_value = 40

        resolution_dropdown = MagicMock()
        resolution_dropdown.selected_option = "1920x1080"

        save_btn = MagicMock()

        self.layout.settings_controls = {
            "master_slider": master_slider,
            "bgm_slider": bgm_slider,
            "sfx_slider": sfx_slider,
            "resolution_dropdown": resolution_dropdown,
            "save_btn": save_btn,
            "fullscreen_value": True,
            "fullscreen_btn": MagicMock()
        }

        event = MagicMock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = save_btn

        # Process event
        handled = self.hud_events.process_event(event)

        self.assertTrue(handled)

        # Verify settings updated
        self.assertEqual(self.settings_service.get("audio", "master_volume"), 0.8)
        self.assertEqual(self.settings_service.get("audio", "bgm_volume"), 0.6)
        self.assertEqual(self.settings_service.get("audio", "sfx_volume"), 0.4)
        self.assertEqual(self.settings_service.get("window", "width"), 1920)
        self.assertEqual(self.settings_service.get("window", "height"), 1080)
        self.assertEqual(self.settings_service.get("window", "fullscreen"), True)

        # Verify resolution changed event published
        self.event_bus.publish.assert_called()
        # Find ResolutionChangedEvent in calls
        found = False
        for call in self.event_bus.publish.call_args_list:
            arg = call[0][0]
            if isinstance(arg, ResolutionChangedEvent):
                self.assertEqual(arg.width, 1920)
                self.assertEqual(arg.height, 1080)
                self.assertTrue(arg.fullscreen)
                found = True
                break
        self.assertTrue(found)

    def test_hud_cancel_settings(self) -> None:
        """
        Tests canceling settings changes from the HUD UI.
        """
        # Initial settings
        self.settings_service.set("audio", "master_volume", 0.5)
        self.audio_manager.set_master_volume(0.5)

        cancel_btn = MagicMock()
        self.layout.settings_controls["cancel_btn"] = cancel_btn

        # Simulate changing volume via slider first
        self.audio_manager.set_master_volume(1.0)

        event = MagicMock(spec=pygame.event.Event)
        event.type = pygame_gui.UI_BUTTON_PRESSED
        event.ui_element = cancel_btn

        # Process event
        handled = self.hud_events.process_event(event)

        self.assertTrue(handled)

        # Verify audio settings reverted to saved service value (0.5)
        self.assertEqual(self.audio_manager.master_volume, 0.5)
        self.layout.close_settings_window.assert_called_once()

if __name__ == '__main__':
    unittest.main()
