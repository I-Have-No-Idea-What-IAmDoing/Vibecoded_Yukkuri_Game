# Implementation Tasks

This document outlines the actionable steps to implement the Personality and Relationship system designed in `personality_relationship_system.md`.

## Phase 1: Data & Components

### 1.1 Define Trait Data Structure
- [ ] Create `data/traits/traits.toml`.
- [ ] Define schema for Traits:
    -   `name`, `description`, `conflicts` (list of strings).
    -   `stat_modifiers` (dict of multipliers/offsets).
    -   `ai_modifiers` (dict mapping Consideration names to curve params).
- [ ] Add initial traits: "Glutton", "Loner", "Friendly", "Aggressive", "Lazy".

### 1.2 Create ECS Components
- [ ] Create `Personality` component in `src/yukkuri_game/game/yukkuri_components.py`.
    -   `traits: List[str]`
- [ ] Create `Relations` component in `src/yukkuri_game/game/yukkuri_components.py`.
    -   `relationships: Dict[int, RelationshipData]` (Use a dataclass for `RelationshipData`).

### 1.3 Update Entity Factory
- [ ] Update `EntityFactory` to attach `Personality` and `Relations` components to Yukkuris.
- [ ] Implement random trait assignment logic based on configuration (e.g., 1-3 random traits per Yukkuri).

## Phase 2: Core Systems Logic

### 2.1 Trait Manager / Service
- [ ] Create `TraitService` (or similar) to load `traits.toml` and provide lookup.
- [ ] Implement helper functions to apply trait modifiers to values (e.g., `apply_stat_modifier(entity_id, stat_name, base_value)`).

### 2.2 Update Utility AI Engine
- [ ] Modify `UtilityAIEngine.select_action` or `UtilitySelector` to account for traits.
- [ ] **Crucial**: Allow dynamic override of Consideration parameters.
    -   When scoring `Consideration`, check if the entity has a Trait that overrides this Consideration's `curve` or `params`.
    -   Example: If `action="Talk"` and `consideration="Loneliness"`, and Trait="Loner" defines an override for "Loneliness", use the Trait's params.

### 2.3 Update Stat System
- [ ] Update `StatDecaySystem` (if it exists, or wherever stats update) to query `Personality` for decay rates.
    -   `decay_rate = base_decay * trait_modifier`.

## Phase 3: Relationship Mechanics

### 3.1 Relationship Management
- [ ] Create `RelationshipSystem` (or add to `GameService`).
- [ ] Implement `get_affinity(entity_a, entity_b)`.
    -   Base: 0.
    -   Modifiers: Compatibility (compare Traits of A and B).
- [ ] Implement `update_affinity(entity_a, entity_b, amount)`.
    -   Clamp between -100 and 100.

### 3.2 Enhanced Social Interactions
- [ ] Update `SocialInteract` action in Behavior Tree.
- [ ] Instead of guaranteed success, calculate outcome chance.
- [ ] On success: Call `update_affinity(+, +)`.
- [ ] On failure: Call `update_affinity(-, -)`.

## Phase 4: Integration & Content

### 4.1 Update AI Actions (TOML)
- [ ] Review `data/ai/actions.toml`. Ensure Consideration names are consistent so they can be referenced by Traits.

### 4.2 Debugging Tools
- [ ] Update "Entity Info" UI to display:
    -   List of Traits.
    -   List of known Relationships (e.g., "Likes Reimu #42").

## Phase 5: Verification
- [ ] Test: Spawn "Loner" Yukkuri. Verify Social need drops slower.
- [ ] Test: Spawn "Glutton". Verify Hunger drops faster.
- [ ] Test: Spawn two incompatible Yukkuris. Verify they don't interact or fight.
