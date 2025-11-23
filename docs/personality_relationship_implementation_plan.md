# Personality and Relationship System Implementation Plan

This plan outlines the steps to implement the design specified in `personality_relationship_system_design.md`.

## Phase 1: Core Components & Data Structures

### Task 1.1: Define Data Classes
- [ ] Create `RelationshipData` dataclass (helper, not component).
- [ ] Create `Personality` component in `src/yukkuri_game/game/yukkuri_components.py`.
    - Attributes: `traits` (Set[str]), `values` (Dict[str, float]), `attitude` (str).
- [ ] Create `RelationshipRegistry` component in `src/yukkuri_game/game/yukkuri_components.py`.
    - Attributes: `relationships` (Dict[int, RelationshipData]), `parents` (List[int]), `children` (List[int]), `mate_id` (Optional[int]).

### Task 1.2: Update Entity Factory
- [ ] Modify `EntityFactory` (`src/yukkuri_game/game/entity_factory.py`) to attach these new components when creating a Yukkuri.
- [ ] Implement a `PersonalityGenerator` service/helper to randomize traits based on Yukkuri type/quality.

## Phase 2: System Logic & Integration

### Task 2.1: Relationship System/Service
- [ ] Create `RelationshipSystem` or extend `SocialSystem` (if exists) to handle:
    - Registering new contacts (First Impressions).
    - Decaying temporary stats (e.g., transient anger).
    - Updating relationship values based on events.

### Task 2.2: Update Utility Selector
- [ ] Modify `UtilitySelector.update` in `src/yukkuri_game/game/ai/utility_selector.py`.
- [ ] Extract `Personality` and `RelationshipRegistry` components.
- [ ] Expand the `context` dictionary:
    - Flatten `traits` into `trait_{name} = 1.0`.
    - Flatten `values` into `value_{name} = value`.
    - Calculate aggregate social stats (e.g., `nearest_enemy_distance`, `nearest_friend_distance`).

## Phase 3: Interaction Logic

### Task 3.1: Action Definitions
- [ ] Update `actions.toml` (or `UtilityAIEngine` configuration) to include scorers that use the new context keys.
    - Example: `Eat` action priority modulated by `trait_GLUTTON`.
    - Example: `Socialize` action priority modulated by `trait_LONER` (negative).

### Task 3.2: Event Handling
- [ ] Implement an event listener for game events (e.g., `DamageTaken`, `FoodShared`).
- [ ] Update `RelationshipRegistry` in response to events.
    - If Entity A hits Entity B -> Entity B increases `Fear` and decreases `Affinity` towards A.

## Phase 4: UI & Debugging

### Task 4.1: Inspector UI
- [ ] Update the inspection UI (if exists) to display:
    - Current Personality Traits.
    - List of known relationships and their status (Affinity/Fear bars).

### Task 4.2: Visual Cues (Optional)
- [ ] Add `FloatingText` triggers for relationship shifts (e.g., "♥" for affinity up, "!" for fear).

## Dependencies
- `pymunk`: Physics engine (already present).
- `py_trees`: Behavior trees (already present).

## Riskiest Assumptions
- The `UtilityAIEngine` supports dynamic context keys without code changes (Need to verify if scorers are hardcoded or data-driven).
- Performance impact of checking relationships every tick (Should optimize to only check nearest or throttle updates).
