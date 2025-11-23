# Actionable Tasks for Proposal 2

## Phase 1: Core Data Structures & Components

- [ ] **Refactor `Personality` Component**
    - [ ] Add `curiosity`, `aggression`, `social`, `rationality` float fields (default 0.0).
    - [ ] Add `pleasure`, `arousal`, `dominance` float fields (default 0.0).
    - [ ] Migrate existing `mood` string logic to map to/from PAD values for backward compatibility initially.

- [ ] **Refactor `RelationshipData`**
    - [ ] Rename `fear` to `respect` (or keep both if distinct).
    - [ ] Ensure `affinity`, `trust`, `respect` use a consistent scale (-100 to 100).
    - [ ] Add `long_term_summary` dictionary to `RelationshipData`.

- [ ] **Create `SocialRules` Config**
    - [ ] Create a configuration (TOML/Python) defining how specific Traits modify Base Vectors (e.g., `Predator` -> +0.5 Aggression).

## Phase 2: System Logic Updates

- [ ] **Update `SocialSystem.on_social_interaction`**
    - [ ] Implement "Event Broadcasting": Find entities within radius `r` of the interaction.
    - [ ] Calculate impact for witnesses based on their relationship to Actor and Target.

- [ ] **Implement `MemoryConsolidation` Logic**
    - [ ] Create a function `consolidate_memories(entity)` in `SocialSystem` (or a new `MemorySystem`).
    - [ ] Iterate through `short_term_memories`.
    - [ ] Apply weighted impact to `affinity`/`trust`/`respect` based on the event type and time passed.
    - [ ] Clear processed short-term memories (or move them to a "faded" state).

- [ ] **Implement PAD Mood Decay & Update**
    - [ ] Update `SocialSystem` to decay `arousal` towards 0 (calm) and `pleasure`/`dominance` towards baseline personality values.
    - [ ] Interactions now impart Delta-P, Delta-A, Delta-D instead of setting fixed Moods.

## Phase 3: Behavior Integration

- [ ] **Update `Behavior` System**
    - [ ] Modify decision-making logic to use PAD values.
        - *Example*: If `arousal` > 80 and `dominance` > 50 -> High chance of Aggressive action.
        - *Example*: If `pleasure` < -50 and `dominance` < -50 -> High chance of Crying/Hiding.

- [ ] **Update Visual Feedback**
    - [ ] Debug tools to visualize the PAD state (e.g., color tinting or debug text).

## Phase 4: Migration & Cleanup

- [ ] **Migration Script**
    - [ ] Convert existing entities' string-based Moods to approximate PAD vectors.
- [ ] **Deprecation**
    - [ ] Remove old discrete `mood` field once all systems use PAD.
