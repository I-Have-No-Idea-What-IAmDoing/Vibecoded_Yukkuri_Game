# Proposal 6: Asset Pipeline Optimizations

## 1. Introduction
Rendering many individual sprites causes significant overhead due to texture state changes in the GPU (or blit overhead in software) and memory fragmentation. Additionally, loading all game data at startup increases initial footprint and load times.

## 2. Problem
- **Texture Swapping**: Drawing 100 different 32x32 images requires 100 source surfaces.
- **Startup Overhead**: `load_all_data` parses every TOML file immediately, even for items or types not present in the current scene.

## 3. Proposed Solution

### 3.1 Texture Atlases
Implement a system to pack small sprites into larger texture sheets (Atlases).
- **Runtime Packing**: On startup, scan `assets/images`, pack them into 1024x1024 (or similar) surfaces using a bin-packing algorithm (e.g., `MaxRects`).
- **SurfaceCache Integration**: The cache stores keys that point to `(AtlasSurface, Rect)` instead of individual Surfaces.
- **Benefits**: Reduced memory overhead (fewer Python objects), better locality.

### 3.2 Lazy Data Loading
Refactor `ResourceManager` to defer parsing of TOML data.
- **Proxy Objects**: `self.yukkuri_types` becomes a dict-like object. Accessing `self.yukkuri_types["Reimu"]` triggers the file load/parse if not already cached.
- **Memory Impact**: Only data relevant to the current session is stored in RAM.

## 4. Risks
- **Complexity**: Atlas packing logic can be complex to implement efficiently.
- **Stalling**: Lazy loading might cause a frame stutter on first access of a new entity type. (Mitigation: Pre-warm cache during loading screens).
