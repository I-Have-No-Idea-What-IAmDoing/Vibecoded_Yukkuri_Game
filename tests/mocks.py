from typing import List, Dict, Any


class MockAudioManager:
    """
    Mock AudioManager for testing.
    Captures played sounds and allows verification.
    """

    def __init__(self) -> None:
        self.enabled = True
        self.played_sounds: List[str] = []
        self.sounds: Dict[str, Any] = {}
        self.master_volume = 1.0
        self.bgm_volume = 1.0
        self.sfx_volume = 1.0

    def load_from_config(self, config_path: str = "") -> None:
        pass

    def load_sound(self, name: str, filepath: str) -> None:
        self.sounds[name] = "MOCK_SOUND"

    def play_sound(self, name: str) -> None:
        self.played_sounds.append(name)

    def set_master_volume(self, volume: float) -> None:
        self.master_volume = volume

    def set_bgm_volume(self, volume: float) -> None:
        self.bgm_volume = volume

    def set_sfx_volume(self, volume: float) -> None:
        self.sfx_volume = volume

    def set_volume(self, volume: float) -> None:
        self.master_volume = volume

    def reset_mocks(self) -> None:
        self.played_sounds.clear()

    def clear(self) -> None:
        pass
