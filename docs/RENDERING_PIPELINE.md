# Rendering Pipeline

This document describes the command-based rendering architecture used by the Yukkuri Game Engine.

## Architecture Overview

The rendering system uses a **command pattern** to decouple ECS state from the rendering backend:

```
ECS World → RenderSystem → Renderer → Backend → Screen
              (produces)     (sorts)   (draws)
```

## Pipeline Stages

The `RenderSystem.update()` method executes these stages each frame:

| Stage | Description |
|-------|-------------|
| 1. Camera Update | Interpolate position, apply aspect correction |
| 2. Background | Draw cached grid (invalidated on camera move) |
| 3. Visibility Query | Query `SectorMap` for visible entities |
| 4. Entity Processing | Generate `SpriteCommand`, `ShadowCommand`, `LightCommand` |
| 5. Floating Text | Process UI overlays for visible entities |
| 6. Placement Preview | Render ghost sprite for item/yukkuri placement |
| 7. Render Execution | Sort commands by layer/z-index, execute via backend |

## Layer System

Entities are sorted by layer, then by Y-position within each layer:

| Layer | Constant | Purpose |
|-------|----------|---------|
| 0 | `LAYER_BACKGROUND` | Grid, terrain |
| 1 | `LAYER_SHADOWS` | Drop shadows (rendered before sprites) |
| 2 | `LAYER_ENTITIES` | Sprites, characters, items |
| 3 | `LAYER_EFFECTS` | Lights, particles, FX |
| 10 | `LAYER_UI` | Floating text, selection highlights |

## Render Commands

All visual elements are represented as immutable command objects:

| Command | Fields | Purpose |
|---------|--------|---------|
| `SpriteCommand` | image, position, alpha, cache_key | Rendered sprites |
| `ShadowCommand` | position, radius, color | Drop shadow ellipses |
| `LightCommand` | position, radius, color, intensity | Dynamic lights |
| `TextCommand` | text, position, size, color | Floating text overlays |
| `OccluderCommand` | vertices, static | Shadow-casting geometry |

## Performance Optimizations

### Spatial Culling
- `SectorMap` provides O(1) spatial queries
- Only entities within screen bounds (+500px buffer) are processed
- `VISIBILITY_BUFFER` constant controls buffer size

### Caching
- **Background Cache**: Grid is pre-rendered to a surface, invalidated on camera movement
- **Surface Cache**: Transformed sprites are cached by (image, frame, scale, rotation, flip) tuple

### Scale Quantization
Sprite scales are quantized to 0.05 increments to prevent cache thrashing:
```python
scale = round(raw_scale * 20.0) / 20.0
```

## Backend Abstraction

The `RenderBackend` interface allows multiple implementations:

| Backend | Status | Notes |
|---------|--------|-------|
| `PygameBackend` | ✅ Active | Software rendering, software lighting |
| `OpenGLBackend` | ⚠️ Broken | Hardware lighting (disabled) |

## Key Files

| File | Purpose |
|------|---------|
| [render_system.py](file:///c:/Users/gamin/OneDrive/Documents/Git/Vibecoded_Yukkuri_Game/src/yukkuri_game/game/systems/render_system.py) | Main pipeline, command generation |
| [renderer.py](file:///c:/Users/gamin/OneDrive/Documents/Git/Vibecoded_Yukkuri_Game/src/yukkuri_game/game/renderer/renderer.py) | Command sorting, backend dispatch |
| [pygame_backend.py](file:///c:/Users/gamin/OneDrive/Documents/Git/Vibecoded_Yukkuri_Game/src/yukkuri_game/game/renderer/pygame_backend.py) | Pygame draw implementation |
| [commands.py](file:///c:/Users/gamin/OneDrive/Documents/Git/Vibecoded_Yukkuri_Game/src/yukkuri_game/game/renderer/commands.py) | Command dataclasses |
| [surface_cache.py](file:///c:/Users/gamin/OneDrive/Documents/Git/Vibecoded_Yukkuri_Game/src/yukkuri_game/game/surface_cache.py) | Sprite transformation cache |
