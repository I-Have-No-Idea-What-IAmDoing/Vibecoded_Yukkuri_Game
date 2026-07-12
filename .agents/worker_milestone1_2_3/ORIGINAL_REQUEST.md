## 2026-06-21T18:22:26Z
Implement Milestones 1, 2, and 3 (dynamic sprite/atlas loading, animator system, and FFI state/action sync) following the design specifications from Explorer 1 and Explorer 2.

Inputs:
- Read c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\explorer_rendering_1\analysis.md and handoff.md.
- Read c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\explorer_rendering_2\analysis.md and handoff.md.
- Read the files: data/yukkuris/types.toml, src/prefabs/mod.rs, src/ai/mod.rs, src/lib.rs, src/main.rs.

Implementation Steps:
1. Create a new module `src/render/mod.rs` containing:
   - Config structures (`YukkuriTypesToml`, `YukkuriTypeConfig`, `AnimationDefConfig`) matching the data/yukkuris/types.toml schema.
   - Logical rendering/animation components: `YukkuriSprite` and `Animator` (including manual_override and ai_action_at_override fields).
   - Resources: `YukkuriTypeRegistry` and `TextureAtlasRegistry`.
   - Event: `AnimationEvent` (emitted on frame matches).
   - A synchronous PNG header parser to read image dimensions from disk so that Bevy TextureAtlasLayout structures can be synchronously initialized at startup.
   - Startup system `setup_graphics_assets_system` that parses types.toml, creates TextureAtlasLayouts, and populates registries.
   - System `update_yukkuri_sprite_system` which maps `YukkuriSprite` current_frame/flip/alpha to Bevy's native `Sprite` and `TextureAtlas` (Bevy 0.19 uses Sprite with an optional texture_atlas field).
   - System `update_animator_system` which ticks the logical `Animator` component (handling loop, ping_pong, speed, frame duration, frame-specific events).
   - Plugin `YukkuriRenderPlugin` registering the systems, resources, and event.
2. In `src/prefabs/mod.rs`:
   - Modify `spawn_yukkuri_prefab` to lookup the entity's type config, initialize `YukkuriSprite` and `Animator`, spawn them alongside Bevy's native `Sprite`/`TextureAtlas` components, and set the visual scale (0.5 for Baby, 0.75 for Child, 1.0 for Adult) on the `Transform` component.
3. In `src/ai/mod.rs`:
   - Process `CommandType::PlayAnimation` in `apply_ai_commands` (updating the animator state and locking `manual_override = true`).
   - Implement `sync_yukkuri_animations` system: maps `AIState::current_action` to lowercase and flight states (swooping -> "swoop", other airborne -> "fly") to animator, respecting the manual override lock (releasing it if the current action changes from the one when override was set).
   - Register the animation sync system in the `AIPlugin`.
4. In `src/lib.rs`:
   - Export the `render` module.
5. In `src/main.rs`:
   - Add `YukkuriRenderPlugin` to the Bevy App.
