# Proposal 7: Engine Scalability & Optimization

## 1. Introduction
To support thousands of simultaneous entities (swarm simulation), the engine must minimize the memory footprint per entity and reduce CPU cycles spent on off-screen or distant entities.

## 2. Problem
- **Redundant Data**: Every `YukkuriStats` component stores a full copy of static data (growth rates, base stats), wasting memory.
- **Uniform Update Cost**: Entities are updated every frame regardless of importance or visibility.
- **Object Overhead**: Python objects have significant per-instance overhead.

## 3. Proposed Solution

### 3.1 Flyweight Pattern for Stats
Refactor `YukkuriStats` to separate dynamic state (age, discipline) from static configuration (base stats, type info).
- **YukkuriArchetype**: Immutable object shared by all instances of a type.
- **YukkuriStats**: Lightweight component referencing the Archetype.

### 3.2 Level of Detail (LOD) System
Implement an `LODSystem` that assigns an importance score to entities based on distance from camera and priority.
- **High LOD**: Full update every frame, full animation.
- **Medium LOD**: Update logic every 2nd frame, simplified animation.
- **Low LOD**: Update logic every 4th frame, no animation (static sprite).
- **Culling**: No rendering for off-screen entities.

### 3.3 Component Improvements
- **Spatial Partitioning**: Implement a Spatial Hash Grid to quickly query "entities in view" for the LOD system.
- **Slots**: Ensure ALL components use `__slots__` (already largely done, but enforce strict compliance).

## 4. Risks
- **LOD Popping**: Visual artifacts when switching LOD levels.
- **Logic Desync**: Physics/AI might behave differently at lower update rates. (Mitigation: Accumulate `dt` for low-LOD updates).
