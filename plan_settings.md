# Settings & Audio

## 1. Overview
This plan adds a Settings Menu to control Audio (Volume) and Window settings.

## 2. Configuration Persistence
*   **File**: `src/yukkuri_game/config.py`
    *   **Action**: Add `AudioConfig` and `DisplayConfig` sections.
    *   **Attributes**: `master_volume`, `bgm_volume`, `sfx_volume`, `fullscreen`, `window_width`, `window_height`.
    *   **Action**: Ensure `GameConfig` loads/saves these values.

## 3. Audio Manager Updates
*   **File**: `src/yukkuri_game/engine/audio.py`
    *   **Action**: Add `set_master_volume(vol)`, `set_bgm_volume(vol)`, `set_sfx_volume(vol)`.
    *   **Action**: Update sound playing logic to respect these volumes.

## 4. UI Implementation
*   **File**: `src/yukkuri_game/game/ui/settings_menu.py` (New File)
    *   **Action**: Create `SettingsWindow` using `pygame_gui`.
    *   **Elements**:
        *   Sliders for Volumes.
        *   Checkbox for Fullscreen.
        *   Dropdown/Input for Resolution.
        *   "Save" and "Close" buttons.
*   **File**: `src/yukkuri_game/game/ui/hud.py`
    *   **Action**: Add "Settings" button to main HUD.
    *   **Action**: Handle event to open `SettingsWindow`.

## 5. Game Manager Integration
*   **File**: `src/yukkuri_game/game/game_manager.py`
    *   **Action**: Listen for `SettingsChangedEvent`.
    *   **Action**: Apply resolution changes (might require window recreation or `pygame.display.set_mode`).

## 6. Pre-commit Steps
*   **Action**: Ensure proper testing, verification, review, and reflection are done.

## 7. Verification
*   **Test**: Open settings, change volume, verify audio level changes. Change resolution, verify window resize.
