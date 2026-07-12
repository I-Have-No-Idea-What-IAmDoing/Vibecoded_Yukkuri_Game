# Handoff Report — Explorer Rendering 1

This handoff report summarizes the read-only investigation and design of the dynamic texture/atlas loading (R1) and Animator component/system (R2) for the Rust/Bevy 0.19 port.

---

## 1. Observation

- **Bevy Version & Package Configurations**:
  - `Cargo.toml` lines 7-8:
    ```toml
    bevy = "0.19.0"
    avian2d = "0.7.0"
    ```
- **Existing Prefab Spawner**:
  - `src/prefabs/mod.rs` (lines 61-96) spawns rigid bodies, colliders, needs, stats, and stable IDs, but lacks any rendering (`Sprite`, `TextureAtlas`, or `Animator`) components.
- **Python Component References**:
  - `src/yukkuri_game/engine/components.py` lines 62-98 define `Sprite` and `Animator` structures.
  - `src/yukkuri_game/game/yukkuri_constants.py` lines 12-19 define growth stage names and scale factors:
    ```python
    STAGE_BABY = "Baby"
    STAGE_CHILD = "Child"
    STAGE_ADULT = "Adult"
    SCALE_BABY = 0.5
    SCALE_CHILD = 0.75
    SCALE_ADULT = 1.0
    ```
- **Image Assets**:
  - The `assets/images` directory contains sprite sheets like `reimu_eat.png` (256x64) and `reimu_play.png` (256x64), which are multiple frames of size 64x64.
- **Animation Definitions**:
  - `data/yukkuris/types.toml` defines general yukkuri properties like name, image, width, height, and health, but does not yet contain configured animation sections. The python code has fallbacks if no animations are configured.

---

## 2. Logic Chain

- **Step 1**: Because Bevy is at version `0.19.0`, we must use Bevy 0.19's native `Sprite` and `TextureAtlas` (consisting of `layout: Handle<TextureAtlasLayout>` and `index: usize`) for sprite-sheet rendering.
- **Step 2**: Because Bevy asset loading is asynchronous, we cannot synchronously retrieve image dimensions from `Handle<Image>` to build `TextureAtlasLayout` structures on startup.
- **Step 3**: By using a synchronous PNG header parser, we can read the PNG header from disk to extract overall width and height, enabling synchronous construction of `TextureAtlasLayout`s at setup time.
- **Step 4**: Isolating Bevy's asset handles from the FFI boundary requires designing custom `YukkuriSprite` and `Animator` components in Rust, which are updated via gameplay systems and then synchronized to Bevy's native components.
- **Step 5**: Based on growth stages (`Baby` -> 0.5, `Child` -> 0.75, `Adult` -> 1.0), the entity's visual scale is set on Bevy's standard `Transform` component during prefab spawning.

---

## 3. Caveats

- **Sprite Alignment**: Assumed that all sprite sheets are horizontally aligned (columns = width / frame_width, rows = 1). This is confirmed by checking `reimu_eat.png` (256x64) vs frame size (64x64).
- **Format Limitation**: Assumed that only PNG images are animated (since `bed.jpg` is a static JPEG). The PNG header parser only parses PNG files, falling back to frame size as sheet size if parsing fails.
- **Agility Stat**: The `agility` field is not currently in the Rust `YukkuriStats` struct. This will need to be added or defaulted to 1.0.

---

## 4. Conclusion

We have fully designed R1 (dynamic texture/atlas loading) and R2 (Animator component/system) for Rust and Bevy 0.19.0, specifying all structures, registry resources, and update/sync systems. The design is detailed in `analysis.md` inside this directory.

---

## 5. Verification Method

- **Compile Test**: Run `cargo check` to verify the project continues to compile.
- **Integration Test**: Build a test file `tests/rendering_camera_test.rs` that:
  1. Initializes a headless Bevy app with `AIPlugin` and `RenderPlugin`.
  2. Spawns an entity via `spawn_yukkuri_prefab` and asserts that `YukkuriSprite`, `Animator`, and Bevy's native `Sprite` component are attached with correct scales and index.
  3. Steps the application and verifies frame tick advances, ping-pong direction flips, and animation events are fired.
  4. Triggers `CommandType::PlayAnimation` and asserts that the active animation swaps.
