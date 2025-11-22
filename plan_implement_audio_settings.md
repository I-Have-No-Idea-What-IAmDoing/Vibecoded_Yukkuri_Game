# Plan: Implement Audio Settings (UX)

This plan specifically focuses on the Audio Settings UI and persistence, acting as a detailed implementation guide for the Audio portion of the Settings Menu.

## 1. UI Implementation Details

- **Widget Library**: `pygame_gui`.
- **Elements**:
    - `UIHorizontalSlider` for Master, BGM, SFX.
        - Range: 0.0 to 1.0 (or 0 to 100).
        - Start value: Get from `AudioManager`.
    - `UILabel` for values (optional, to show "50%").

- **Interaction**:
    - On Slider Changed Event (`pygame_gui.UI_HORIZONTAL_SLIDER_MOVED`):
        - specific slider -> `AudioManager.set_volume(value)`.
        - Update label text if present.

## 2. Persistence (Audio Specifics)

- **Config File**: `user_settings.json` (or within main config).
- **Load**:
    - On `AudioManager` init or `GameManager` init, read config.
    - Call `AudioManager.set_volume` (and specific channels).
- **Save**:
    - On "Save Settings" button press or Slider release (auto-save?).
    - Write to `user_settings.json`.

## 3. Integration with Task 2
- This plan feeds into the "Settings Window" creation in Task 2.
- It defines the *behavior* of the audio controls inside that window.

## 4. Verification
- Change volume slider -> Hearing change immediately?
- Close game -> Reopen -> Volume slider is at saved position? Audio level matches?

## 5. Pre-commit
- Ensure proper testing, verification, review, and reflection are done.
