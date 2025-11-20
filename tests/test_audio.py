import unittest
from src.utils.audio_manager import AudioManager

class TestAudioManager(unittest.TestCase):
    def test_initialization(self):
        # Should not crash even if pygame mixer fails (e.g. headless)
        # AudioManager catches ImportError/PygameError
        config = {"music_volume": 0.8, "sfx_volume": 0.2}
        manager = AudioManager(config)

        self.assertEqual(manager.music_volume, 0.8)
        self.assertEqual(manager.sfx_volume, 0.2)

    def test_load_play_safe(self):
        # Ensure calling play methods without files doesn't crash
        manager = AudioManager()
        manager.play_sound("nonexistent")
        manager.play_music("nonexistent.mp3")
        manager.stop_music()

        # Success is just not crashing

if __name__ == "__main__":
    unittest.main()
