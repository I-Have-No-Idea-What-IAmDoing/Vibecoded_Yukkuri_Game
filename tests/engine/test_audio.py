import pytest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.engine.audio import AudioManager

@pytest.fixture
def mock_pygame_mixer():
    with patch('pygame.mixer') as mock_mixer:
        mock_mixer.Sound = MagicMock()
        yield mock_mixer

@pytest.fixture
def audio_manager(mock_pygame_mixer):
    return AudioManager()

def test_audio_manager_init_success(mock_pygame_mixer):
    """Test successful initialization of AudioManager."""
    am = AudioManager()
    assert am.enabled is True
    mock_pygame_mixer.init.assert_called_once()
    assert am.volume == 0.5
    assert am.sounds == {}

def test_audio_manager_init_failure():
    """Test initialization failure when pygame.error is raised."""
    with patch('pygame.mixer.init', side_effect=pygame.error("No device")):
        am = AudioManager()
        assert am.enabled is False

def test_load_sound_success(audio_manager, mock_pygame_mixer):
    """Test loading a sound successfully."""
    with patch('os.path.exists', return_value=True):
        audio_manager.load_sound("test_sound", "path/to/sound.wav")

        assert "test_sound" in audio_manager.sounds
        mock_pygame_mixer.Sound.assert_called_with("path/to/sound.wav")
        audio_manager.sounds["test_sound"].set_volume.assert_called_with(0.5)

def test_load_sound_file_not_found(audio_manager):
    """Test loading a sound that does not exist."""
    with patch('os.path.exists', return_value=False):
        audio_manager.load_sound("test_sound", "nonexistent.wav")
        assert "test_sound" not in audio_manager.sounds

def test_load_sound_disabled(mock_pygame_mixer):
    """Test loading sound when audio is disabled."""
    with patch('pygame.mixer.init', side_effect=pygame.error("No device")):
        am = AudioManager()
        am.load_sound("test", "path.wav")
        assert "test" not in am.sounds

def test_load_sound_exception(audio_manager):
    """Test exception handling during sound loading."""
    with patch('os.path.exists', return_value=True):
        # We need to mock AudioManager.sounds before calling load_sound,
        # or ensure we are patching where it's used.
        # In `audio.py`: `self.sounds[name] = pygame.mixer.Sound(filepath)`
        # The exception happens at `pygame.mixer.Sound`.

        # The issue might be that I am using `audio_manager` fixture which uses `mock_pygame_mixer` fixture.
        # `mock_pygame_mixer` patches `pygame.mixer` and sets `Sound` to a MagicMock.
        # Here I am trying to patch `pygame.mixer.Sound` again.

        # Instead of patching again, let's configure the existing mock.
        pygame.mixer.Sound.side_effect = Exception("Load error")

        audio_manager.load_sound("broken", "path.wav")
        assert "broken" not in audio_manager.sounds

        # Reset side effect for other tests if shared (though fixtures scope function usually)
        pygame.mixer.Sound.side_effect = None

def test_play_sound(audio_manager, mock_pygame_mixer):
    """Test playing a sound."""
    mock_sound = MagicMock()
    audio_manager.sounds["test"] = mock_sound

    audio_manager.play_sound("test")
    mock_sound.play.assert_called_once()

def test_play_sound_not_found(audio_manager):
    """Test playing a sound that hasn't been loaded."""
    audio_manager.play_sound("missing")
    # Should not raise error

def test_play_sound_disabled(mock_pygame_mixer):
    """Test playing sound when disabled."""
    with patch('pygame.mixer.init', side_effect=pygame.error("No device")):
        am = AudioManager()
        am.play_sound("test")
        # Should do nothing

def test_set_volume(audio_manager):
    """Test setting volume."""
    mock_sound1 = MagicMock()
    mock_sound2 = MagicMock()
    audio_manager.sounds["s1"] = mock_sound1
    audio_manager.sounds["s2"] = mock_sound2

    audio_manager.set_volume(0.8)

    assert audio_manager.volume == 0.8
    mock_sound1.set_volume.assert_called_with(0.8)
    mock_sound2.set_volume.assert_called_with(0.8)

def test_set_volume_clamping(audio_manager):
    """Test that volume is clamped between 0.0 and 1.0."""
    audio_manager.set_volume(1.5)
    assert audio_manager.volume == 1.0

    audio_manager.set_volume(-0.5)
    assert audio_manager.volume == 0.0
