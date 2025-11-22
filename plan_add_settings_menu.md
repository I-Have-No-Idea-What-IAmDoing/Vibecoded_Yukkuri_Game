# Plan: Add Settings Menu

This plan covers adding a comprehensive Settings Menu including Volume Sliders and Window/Fullscreen toggles.

## 1. Backend Support

### 1.1 Update `AudioManager`
- File: `src/yukkuri_game/engine/audio.py`
- Add support for separate volume channels:
    - `master_volume` (0.0 - 1.0)
    - `bgm_volume` (0.0 - 1.0)
    - `sfx_volume` (0.0 - 1.0)
- Update `set_volume` to accept channel type or update `play_sound` to use specific channel volume * master volume.
- Add `set_bgm_volume`, `set_sfx_volume`.
- Store these values.

### 1.2 Update `GameConfig` (Optional but recommended)
- If `GameConfig` exists, add fields for persistent settings (Resolution, Fullscreen, Volumes).

## 2. UI Implementation (`HudLayout`)

### 2.1 Add Settings Button
- File: `src/yukkuri_game/game/ui/hud_layout.py`
- Add a "Settings" button to the Top Bar (`_create_top_bar`).

### 2.2 Create Settings Window
- File: `src/yukkuri_game/game/ui/hud_layout.py`
- Create a `SettingsWindow` class or a method `create_settings_window()`.
- Window elements:
    - **Audio Section**:
        - Label: "Master Volume" + Horizontal Slider.
        - Label: "BGM Volume" + Horizontal Slider.
        - Label: "SFX Volume" + Horizontal Slider.
    - **Video Section**:
        - Label: "Resolution" + Dropdown (800x600, 1024x768, 1280x720, 1920x1080).
        - Checkbox/Button: "Fullscreen".
    - **Buttons**: "Save", "Close".

### 2.3 Handle UI Events
- File: `src/yukkuri_game/game/ui/hud_renderer.py` or `hud_events.py` (or `Yukkurrium` input handling).
- Listen for slider change events -> Update `AudioManager`.
- Listen for Resolution/Fullscreen changes -> Update `pygame.display`.
    - *Note*: Changing resolution usually requires re-initializing display or using `pygame.display.set_mode`. This might resize the UI Manager too.

## 3. Persistence (Settings)

### 3.1 Save/Load Settings
- Create `src/yukkuri_game/game/settings_manager.py` or use `GameConfig`.
- Load settings on startup (`main.py`).
- Save settings when "Save" is clicked in Settings Menu or on Exit.
- JSON format: `{"master_volume": 0.5, "resolution": [1280, 720], "fullscreen": false, ...}`.

## 4. Verification
- Test opening/closing the menu.
- Test sliders changing volume in real-time.
- Test resolution change (ensure UI adapts).
- Test persistence (restart game, check if settings stick).

## 5. Pre-commit
- Ensure proper testing, verification, review, and reflection are done.
