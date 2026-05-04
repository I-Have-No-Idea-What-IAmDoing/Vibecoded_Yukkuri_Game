# Proposal 4: Unified Spatial Partitioning for AI and Physics

## Overview
Currently, the `SectorMap` is primarily used by the `RenderSystem` for visibility culling. Other systems (Social, Interaction, Perception) often perform $O(N^2)$ checks or maintain their own spatial logic.

## Motivation
- **Performance**: A centralized spatial index allows all systems to perform proximity queries (e.g., "find neighbors") in $O(\log N)$ or $O(1)$ time.
- **Consistency**: All systems will use the same "source of truth" for entity positions and spatial relationships.
- **Simplicity**: Systems can offload complex geometry queries (raycasting, circle casts) to a specialized service.

## Proposed Changes

### 1. Create `SpatialService`
Extract the logic from `SectorMap` and `SectorSystem` into a dedicated `SpatialService` registered in `world.services`.

### 2. Implement core spatial queries
Add methods to `SpatialService` for:
- `get_entities_in_radius(pos, radius)`
- `get_entities_in_rect(rect)`
- `get_nearest_entity(pos, type_filter)`
- `raycast(start, end)` (optional, for LOS checks)

### 3. Automatic Updates
Ensure the `SpatialService` stays in sync with entity `Transform` components, likely via a `SpatialUpdateSystem` that runs after physics.

### 4. Refactor dependent systems
Update `SocialSystem`, `InteractionSystem`, and `PerceptionSystem` to use `SpatialService` for finding targets and neighbors.

## Impact
- **Performance**: Significant reduction in CPU usage when many Yukkuris are present.
- **AI Quality**: Enables more complex spatial behaviors (like flocking or sophisticated social distancing) that were previously too expensive.

## Implementation Phases
1.  **Phase 1**: Design the `SpatialService` API.
2.  **Phase 2**: Implement the service and the update system.
3.  **Phase 3**: Migrate `RenderSystem` visibility query to the new service.
4.  **Phase 4**: Migrate AI and social systems to use the new service for proximity checks.
