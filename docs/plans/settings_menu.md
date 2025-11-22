# Settings Menu & Audio Settings

## Goal
Implement a settings menu allowing control over audio volumes (Master, BGM, SFX) and window settings (resolution, fullscreen). Persist these settings.

## Steps

1.  **Create `SettingsService`**
    -   **File**: `src/yukkuri_game/game/services.py` (or new `settings_service.py`).
    -   Responsibility: Load/Save `user_settings.json`.
    -   Data: `master_volume`, `bgm_volume`, `sfx_volume`, `window_width`, `window_height`, `fullscreen`.

2.  **Update `AudioManager`**
    -   **File**: `src/yukkuri_game/engine/audio.py`
    -   Add methods: `set_master_volume(float)`, `set_bgm_volume(float)`, `set_sfx_volume(float)`.
    -   Ensure sounds played are scaled by these volumes.

3.  **Update `HudLayout` and `HudRenderer`**
    -   **File**: `src/yukkuri_game/game/ui/hud_layout.py`
    -   Add a "Settings" button to the top bar or main menu.
    -   Create a `SettingsWindow` (using `pygame_gui` `UIWindow`).
        -   Sliders for volumes.
        -   Dropdown/Toggle for Resolution/Fullscreen.
        -   "Save" and "Cancel" buttons.

4.  **Implement `SettingsWindow` Logic**
    -   **File**: `src/yukkuri_game/game/ui/hud_renderer.py` (or separate controller).
    -   On "Save": Update `SettingsService`, apply changes to `AudioManager` and `pygame.display`.
    -   On "Cancel": Revert to previous settings.

5.  **Integrate at Startup**
    -   **File**: `src/yukkuri_game/main.py`
    -   Initialize `SettingsService`.
    -   Apply saved settings (Audio, Window size) *before* the game loop starts.

6.  **Verification**
    -   **Test**: Change volume in settings. Verify sound is quieter/louder.
    -   **Test**: Restart game. Verify settings persist.
    -   **Test**: Toggle fullscreen (if supported by environment, otherwise mock).

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
