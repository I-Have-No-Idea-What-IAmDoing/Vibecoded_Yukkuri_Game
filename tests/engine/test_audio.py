import unittest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.engine.audio import AudioManager


class TestAudio(unittest.TestCase):
    def setUp(self):
        # Patch pygame.mixer.init to control successful initialization
        self.mixer_init_patcher = patch("pygame.mixer.init")
        self.mock_mixer_init = self.mixer_init_patcher.start()

    def tearDown(self):
        self.mixer_init_patcher.stop()

    def test_init_success(self) -> None:
        audio = AudioManager()
        self.assertTrue(audio.enabled)
        self.mock_mixer_init.assert_called_once()

    def test_init_failure(self) -> None:
        self.mock_mixer_init.side_effect = pygame.error("No device")
        audio = AudioManager()
        self.assertFalse(audio.enabled)

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_load_sound_success(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        self.assertIn("test", audio.sounds)
        self.assertEqual(audio.sounds["test"], mock_sound_instance)
        # Volume is calculated from master * sfx
        mock_sound_instance.set_volume.assert_called_with(
            audio.master_volume * audio.sfx_volume
        )

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_load_sound_file_not_found(self, mock_exists, mock_sound_class):
        mock_exists.return_value = False

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        self.assertNotIn("test", audio.sounds)
        mock_sound_class.assert_not_called()

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_load_sound_exception(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_class.side_effect = Exception("Load error")

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        self.assertNotIn("test", audio.sounds)

    def test_load_sound_disabled(self) -> None:
        self.mock_mixer_init.side_effect = pygame.error("No device")
        audio = AudioManager()

        with patch("os.path.exists") as mock_exists:
            audio.load_sound("test", "test.wav")
            mock_exists.assert_not_called()

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_play_sound(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        audio.play_sound("test")
        mock_sound_instance.play.assert_called_once()

        audio.play_sound("missing")
        # Should not raise error

    def test_play_sound_disabled(self) -> None:
        self.mock_mixer_init.side_effect = pygame.error("No device")
        audio = AudioManager()
        # Manually inject sound to verify play logic is skipped
        mock_sound = MagicMock()
        audio.sounds["test"] = mock_sound

        audio.play_sound("test")
        mock_sound.play.assert_not_called()

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_set_volume(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        audio.set_master_volume(0.8)
        self.assertEqual(audio.master_volume, 0.8)
        mock_sound_instance.set_volume.assert_called_with(0.8 * audio.sfx_volume)

        # Test clamping
        audio.set_master_volume(1.5)
        self.assertEqual(audio.master_volume, 1.0)

        audio.set_master_volume(-0.5)
        self.assertEqual(audio.master_volume, 0.0)

    @patch("pygame.mixer.music.set_volume")
    @patch("pygame.mixer.get_init")
    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_set_bgm_volume(
        self, mock_exists, mock_sound_class, mock_get_init, mock_music_volume
    ):
        mock_exists.return_value = True
        mock_get_init.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.set_bgm_volume(0.7)

        self.assertEqual(audio.bgm_volume, 0.7)
        mock_music_volume.assert_called_with(audio.master_volume * 0.7)

    @patch("pygame.mixer.music.set_volume")
    @patch("pygame.mixer.get_init")
    def test_set_bgm_volume_clamping(self, mock_get_init, mock_music_volume):
        mock_get_init.return_value = True

        audio = AudioManager()
        audio.set_bgm_volume(1.5)
        self.assertEqual(audio.bgm_volume, 1.0)

        audio.set_bgm_volume(-0.5)
        self.assertEqual(audio.bgm_volume, 0.0)

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_set_sfx_volume(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.load_sound("test", "test.wav")

        audio.set_sfx_volume(0.6)

        self.assertEqual(audio.sfx_volume, 0.6)
        # Volume = master (1.0) * sfx (0.6) = 0.6
        mock_sound_instance.set_volume.assert_called_with(audio.master_volume * 0.6)

    def test_set_sfx_volume_clamping(self) -> None:
        audio = AudioManager()

        audio.set_sfx_volume(1.5)
        self.assertEqual(audio.sfx_volume, 1.0)

        audio.set_sfx_volume(-0.5)
        self.assertEqual(audio.sfx_volume, 0.0)

    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_load_fallback_sounds(self, mock_exists, mock_sound_class):
        mock_exists.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio._load_fallback_sounds()

        # Should have loaded default sounds
        expected_sounds = ["click", "place", "cancel", "sell", "train", "eat", "cry"]
        for sound_name in expected_sounds:
            self.assertIn(sound_name, audio.sounds)

    @patch("yukkuri_game.engine.audio.AudioManager._load_fallback_sounds")
    @patch("os.path.exists")
    def test_load_from_config_file_not_found(self, mock_exists, mock_fallback):
        mock_exists.return_value = False

        audio = AudioManager()
        audio.load_from_config("nonexistent.toml")

        mock_fallback.assert_called_once()

    @patch("pygame.mixer.music.set_volume")
    @patch("pygame.mixer.get_init")
    @patch("pygame.mixer.Sound")
    @patch("os.path.exists")
    def test_update_all_volumes(
        self, mock_exists, mock_sound_class, mock_get_init, mock_music_volume
    ):
        mock_exists.return_value = True
        mock_get_init.return_value = True
        mock_sound_instance = MagicMock()
        mock_sound_class.return_value = mock_sound_instance

        audio = AudioManager()
        audio.load_sound("test1", "test1.wav")
        audio.load_sound("test2", "test2.wav")

        audio.set_master_volume(0.5)

        # All sounds should have been updated
        # master=0.5, sfx=1.0, so volume = 0.5
        self.assertEqual(
            mock_sound_instance.set_volume.call_args[0][0], 0.5 * audio.sfx_volume
        )
        # Music volume should be updated too
        mock_music_volume.assert_called_with(0.5 * audio.bgm_volume)

    def test_update_all_volumes_disabled(self) -> None:
        self.mock_mixer_init.side_effect = pygame.error("No device")
        audio = AudioManager()
        mock_sound = MagicMock()
        audio.sounds["test"] = mock_sound

        # Should not crash when disabled
        audio._update_all_volumes()

        mock_sound.set_volume.assert_not_called()


if __name__ == "__main__":
    unittest.main()
