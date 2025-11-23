# Personality and Relationship System Implementation Tasks

This plan outlines the steps to implement the consolidated design defined in `personality_relationship_system_design.md`.

## Phase 1: Data & Components (Foundation)

### 1.1 Trait Data System
- [ ] Create `data/traits/traits.toml` and define the schema.
    - Sections: `stat_modifiers`, `ai_modifiers`, `interaction_modifiers`.
- [ ] Implement `TraitService` to load and validate traits from TOML.
- [ ] Add initial traits: `GESU`, `NICE`, `GLUTTON`, `LONER`, `COWARD`.

### 1.2 ECS Components
- [ ] Create `Personality` component in `yukkuri_components.py`.
    - Fields: `traits` (Set[str]), `values` (Dict[str, float]), `attitude` (str).
- [ ] Create `RelationshipRegistry` component.
    - Fields: `relationships` (Dict), `parents`, `children`, `mate_id`.
- [ ] Define `RelationshipData` helper class.
    - Fields: `affinity`, `trust`, `fear`, `familiarity`, `memories`.

### 1.3 Entity Factory Updates
- [ ] Update `EntityFactory` to attach new components.
- [ ] Implement `PersonalityGenerator` to assign traits/values at spawn.
    - Support inheritance (parents pass down traits/values).
    - Support random generation based on Yukkuri Type (e.g., Marisa has higher chance of `GLUTTON`).

## Phase 2: Core Systems & AI (The "Brain")

### 2.1 AI Engine Enhancements
- [ ] Modify `UtilitySelector`/`UtilityAIEngine` to support **Curve Overrides**.
    - When scoring considerations, check `Personality` traits for `ai_modifiers`.
    - If a modifier exists, replace the standard curve/params with the trait's version.
- [ ] Update AI Context building.
    - Inject `trait_*` and `value_*` keys.
    - Inject `rel_*` stats for the current target entity.

### 2.2 Stat System Integration
- [ ] Update `StatDecaySystem` (or equivalent) to apply `stat_modifiers` from Traits.
    - Example: `hunger_decay` = `base` * `trait_GLUTTON.multiplier`.

## Phase 3: Relationship Mechanics (The "Heart")

### 3.1 Relationship System
- [ ] Create `RelationshipSystem` to manage social state.
    - `update_relationship(actor, target, affinity_change, trust_change, fear_change)`
    - Handle clamping and decay of temporary values.
    - Update `Familiarity` over time when entities are close.

### 3.2 Interaction Matrix Implementation
- [ ] Implement the logic for the Interaction Matrix.
    - Create a lookup table or service that maps `ActionType` -> Base Delta Values.
    - Apply Trait multipliers (e.g., `COWARD` takes double Fear damage).

## Phase 4: Interaction Logic (Behavior)

### 4.1 Social Actions
- [ ] Update/Create social actions in `actions.toml` and Behavior Tree.
    - `SocialInteract`: Generic interaction that branches based on relationship status.
    - `Bully`: Unlocked by High Fear + `GESU`/`SADIST` trait.
    - `Beg`: Unlocked by Low Status/Hunger.
- [ ] Implement success/fail logic based on Affinity and Compatibility.

### 4.2 Event Handling
- [ ] Wire up game events (`DamageTaken`, `ItemStolen`) to the `RelationshipSystem`.
    - "If I take damage from X, lower Affinity and change Fear based on damage amount."

## Phase 5: UI & Polish

### 5.1 Debug UI
- [ ] Add "Personality" tab to Entity Inspector.
    - Show active Traits and Values.
    - Show list of Relationships (sorted by Affinity).
- [ ] Add visual indicators for Traits (optional icons).

### 5.2 Visual Feedback
- [ ] Implement floating emojis/text for relationship updates.
    - "♥" for affinity gain, "💢" for anger/affinity loss.

## Risks & Mitigation
- **Performance**: The O(N^2) nature of relationships.
    - *Mitigation*: Only track active relationships. Prune interactions that haven't happened in a long time.
- **Complexity**: Balancing the AI curves with Overrides.
    - *Mitigation*: Start with very few Traits (3-4) and simple overrides. Debug thoroughly before adding complex combinations.
