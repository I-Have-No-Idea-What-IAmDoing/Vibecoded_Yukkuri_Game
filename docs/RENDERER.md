# Renderer Documentation

The Yukkuri Game Engine uses a command-based renderer architecture designed for flexibility and performance. It supports both Pygame (Software) and OpenGL (Hardware accelerated) backends.

## Architecture Overview

The rendering pipeline is split into three main layers:

1.  **Render System (`game/systems/render_system.py`)**: An ECS system that queries the world for visible entities, interpolates their positions, and submits "Render Commands" to the Renderer.
2.  **Renderer (`game/renderer/renderer.py`)**: A command aggregator that collects, sorts (by layer and Z-index), and dispatches commands to a Backend.
3.  **Backends (`game/renderer/backend.py`)**: Low-level implementations that perform the actual drawing.
    *   `PygameBackend`: Uses standard Pygame surface operations. Supports software lighting.
    *   `OpenGLBackend`: Uses `pygame_light2d` for hardware-accelerated rendering and advanced lighting/shadows.

## Render Commands

Commands are simple dataclasses defined in `game/renderer/commands.py`. Common commands include:

-   `SpriteCommand`: Draws a sprite image at a specific position. Support scaling, rotation, and selection outlines.
-   `ShadowCommand`: Draws an elliptical shadow beneath entities.
-   `LightCommand`: Defines a light source with radius, intensity, and color.
-   `OccluderCommand`: Defines geometry that casts shadows.
-   `TextCommand`: Draws text for UI or floating labels.

## Lighting and Shadows

The engine supports a dynamic lighting system:

-   **Ambient Light**: Controlled via `RenderSystem.set_ambient_light(color)`.
-   **Light Sources**: Entities with a `LightSource` component emit light.
-   **Shadows**: Entities with an `Occluder` component cast shadows when illuminated by a light source.
-   **Flicker Effects**: Preset styles like `FIRE` or `PULSE` can be applied to light sources.

## Performance Features

-   **Command Sorting**: Ensures correct depth ordering (Y-sorting).
-   **Culling**: Only entities visible within the camera view are processed.
-   **Texture Caching**: `OpenGLBackend` caches Pygame surfaces as OpenGL textures to minimize CPU-to-GPU transfers.
-   **Surface Caching**: `SurfaceCache` handles rotated/scaled sprite variations to avoid redundant processing.

## Usage

To add a new renderable entity:
1.  Add a `Transform` and `Sprite` component.
2.  (Optional) Add `VisualTransform` for shadow offsets.
3.  (Optional) Add `LightSource` or `Occluder` for lighting effects.

The `RenderSystem` will automatically detect and render the entity if it's within the camera bounds.
