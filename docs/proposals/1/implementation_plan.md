# Proposal 1: Refactor RenderSystem into a Pass-Based Pipeline

## Goal Description
The current `RenderSystem` (in `src/yukkuri_game/game/systems/render_system.py`) is a monolithic class (760+ lines) that handles everything from spatial culling and background caching to entity sprite processing, lighting, shadow calculation, and UI overlays. This complexity makes it difficult to maintain, optimize, and extend.

This proposal refactors `RenderSystem` into a composable Pass-Based Pipeline, extracting specific rendering responsibilities into modular `RenderPass` components. 

## User Review Required
> [!NOTE]
> This is the final refinement of the architectural plan. Since breaking backwards compatibility is allowed and encouraged, the legacy `render_system.py` wrapper has been removed from the plan in favor of a clean, fully modern package replacement. If approved, we will begin execution!

## Decisions Made
1. **Full Replacement (Breaking Backwards Compatibility)**: We will delete `src/yukkuri_game/game/systems/render_system.py` entirely and replace it with a clean `RenderingSystem` inside the new `rendering/` package. External systems (`day_night.py`, `gameplay.py`) will be updated to use the new API directly. 
2. **Avoiding Redundant Math**: Instead of a separate `TransformPass` or re-calculating math in every pass, the `CullingPass` will compute the interpolated positions and screen positions *once* and output a list of tuples to the `RenderContext`. This guarantees we iterate over the raw entities only once to do math, and subsequent passes (Sprite, Light, Shadow) iterate over lightweight pre-computed tuples. This is the most memory- and CPU-efficient approach for Python.
3. **State Encapsulation**: The bulky cache state variables (`_background_cache`, `_last_camera_state`) will be stored exclusively inside the `BackgroundPass` instance.

## Proposed Changes

### `src/yukkuri_game/game/systems/rendering/context.py`
#### [NEW] context.py
Define a `RenderContext` data class to share state. 
```python
from dataclasses import dataclass, field
from typing import List, Tuple
from ....engine.ecs import World
from ...camera import Camera
from ...renderer.renderer import Renderer
from ..components import Transform
from ...surface_cache import SurfaceCache

@dataclass
class RenderContext:
    world: World
    renderer: Renderer
    camera: Camera
    sw: int
    sh: int
    alpha: float
    surface_cache: SurfaceCache
    
    # Populated by CullingPass: list of (entity_id, transform, ix, iy, screen_x, screen_y)
    visible_render_data: List[Tuple[int, Transform, float, float, float, float]] = field(default_factory=list)
```

### `src/yukkuri_game/game/systems/rendering/pipeline.py`
#### [NEW] pipeline.py
Define the `RenderPass` Protocol and `RenderPipeline` controller:
```python
from typing import Protocol, Type, TypeVar
from .context import RenderContext

T = TypeVar('T', bound='RenderPass')

class RenderPass(Protocol):
    def execute(self, context: RenderContext) -> None: ...

class RenderPipeline:
    def __init__(self, passes: list[RenderPass]):
        self.passes = passes
        
    def execute(self, context: RenderContext) -> None:
        for p in self.passes:
            p.execute(context)
            
    def get_pass(self, pass_type: Type[T]) -> T | None:
        for p in self.passes:
            if isinstance(p, pass_type):
                return p
        return None
```

### `src/yukkuri_game/game/systems/rendering/passes/`
#### [NEW] __init__.py
#### [NEW] background_pass.py
Extract `_draw_grid`, `_rebuild_background_cache`, and background caching logic. Stores `_background_cache` and `_last_camera_state` as instance variables.
#### [NEW] culling_pass.py
Extract `_get_visible_entities` via `SectorMap`. Iterate over the visible entities, compute interpolated world positions `(ix, iy)` and screen positions `(sx, sy)`, and populate `context.visible_render_data` with tuples.
#### [NEW] shadow_pass.py
Iterates over `visible_render_data` and extracts drop shadow rendering (including `Flight` altitude modifications).
#### [NEW] sprite_pass.py
Iterates over `visible_render_data` and extracts sprite command generation using `SurfaceCache`.
#### [NEW] light_pass.py
Iterates over `visible_render_data` and extracts lighting logic, flicker calculations, and `LightCommand` generation. Will expose `set_ambient_light()` method.
#### [NEW] occluder_pass.py
Iterates over `visible_render_data` and extracts `GeometryUtils.get_occluder_vertices` logic for static and dynamic occluders.
#### [NEW] ui_pass.py
Extract `_process_floating_text` and `_process_placement_preview`. 

### `src/yukkuri_game/game/systems/rendering/system.py`
#### [NEW] system.py
- Creates `RenderingSystem` (inherits from ECS `System`).
- Initializes `RenderPipeline` with the specialized passes during `__init__`.
- The `update` method will:
  1. Compute screen size and apply Camera aspect correction.
  2. Call `renderer.clear_screen()`.
  3. Instantiate `RenderContext` and call `pipeline.execute(context)`.
  4. Call `renderer.render()`.

### External File Updates (Breaking Changes)
#### [DELETE] src/yukkuri_game/game/systems/render_system.py
#### [MODIFY] src/yukkuri_game/scenes/gameplay.py
- Update imports to `from .systems.rendering.system import RenderingSystem`.
- Update world system registration to use `RenderingSystem`.
#### [MODIFY] src/yukkuri_game/game/systems/day_night.py
- Change `world.get_system(RenderSystem).set_ambient_light(color)` to query the new `RenderingSystem`, grab the `LightPass` from the pipeline, and set the ambient light there (or directly on the `Renderer` service if we expose it).

## Verification Plan

### Automated Tests
- Run `uv run scripts/test.py -x --timeout=10 -q` to ensure no headless ECS simulation tests break due to system initialization errors.
- Fix any tests that referenced the old `RenderSystem`.

### Manual Verification
- Launch the game (`uv run scripts/run.py`).
- Verify the background grid renders and scrolls correctly (caching works).
- Verify entities (Yukkuri, items) render with correct Y-sorting, sprites, and shadows.
- Verify day/night cycle lighting works (ambient lighting updates correctly).
- Verify lights flicker and correctly mask occluders.
- Verify placement preview ghost sprites still appear when placing items.
- Verify floating text (e.g., debug or gossip text) appears at the correct screen coordinates.
