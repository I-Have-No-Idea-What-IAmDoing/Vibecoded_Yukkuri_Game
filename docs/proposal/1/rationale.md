# Rationale for Architecture Redesign (Revised)

## Motivation

The current `GameManager` is becoming difficult to maintain due to coupled logic (Input mixed with Gameplay) and hardcoded entity definitions (requiring code changes for balance tweaks). We need to solve these specific problems to allow for faster iteration and safer content addition.

## Benefits

### 1. Safer Content Creation
By moving entity definitions to **Validated Prefabs**, we allow designers to tweak values without touching code, while Schema Validation ensures that typos or invalid values are caught immediately at startup, preventing runtime crashes.

### 2. Clearer Game States
Replacing the monolithic `GameManager` with a **Scene State Machine** clearly separates "Menu Logic" from "Game Logic". The explicit **Shared Context** ensures we know exactly what data persists between these states, eliminating "global variable magic".

### 3. Context-Sensitive Input
The new **Input Contexts** solve the issue of UI inputs conflicting with Gameplay inputs. This removes the need for spaghetti `if not is_menu_open:` checks inside gameplay systems.

### 4. Pragmatic Development
By relaxing "Strict ECS" rules to allow helper methods on components, we reduce boilerplate and make the code more readable. We avoid the "Second System Effect" by rejecting complex features (like a full Scene Stack or Async Event Queue) that are not immediately necessary.

## Trade-offs

### 1. Schema Maintenance
We must maintain schemas for our data files. This adds a step when adding new component types (updating the schema), but pays off by preventing data-rot.

### 2. Refactoring Cost
Existing code relies on `GameManager`. Refactoring to `Application` and `Scene` will require touching `main.py` and the core loop.

## Conclusion
This revised proposal focuses on high-impact, low-risk architectural changes. It prioritizes stability (Validation) and usability (Input Contexts, Helper Methods) over theoretical purity.
