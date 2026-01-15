# AI System Rewrite - Design Rationale

## Why Rewrite?

### Evidence of Current Problems

The existing AI system exhibits several symptoms of technical debt:

#### 1. Code Duplication Creates Divergence

`FindPrey` appears twice in `behavior.py`:
- **Lines 1437-1500**: Used by `build_predator_behavior` (if it exists)
- **Lines 1661-1731**: Used by `build_hunt_behavior`

These implementations have subtle differences:
- Different variable names (`best_target` vs internal logic)
- Different filtering approaches
- Separated maintenance = inevitable divergence

**Impact**: Bug fixes may only be applied to one version.

#### 2. God Object Anti-Pattern

`MoveToTarget.update()` handles:
1. Target position resolution (entity vs coordinate)
2. Visibility checks
3. Close-range direct steering
4. Medium-range line-of-sight checks
5. Physics raycasting
6. Path request management
7. Timeout handling
8. Drift detection with adaptive thresholds
9. Fallback direct movement
10. Path following delegation

**Impact**: Any change risks breaking unrelated functionality.

#### 3. Magic Numbers Resist Tuning

Example from `MoveToTarget`:
```python
if dist_to_target < 150.0:  # Why 150?
    use_direct_steering = True
elif dist_to_target < 400.0:  # Why 400?
    # ...
if (now - request_timestamp) > 0.5:  # Why 0.5s timeout?
```

**Impact**: Gameplay tuning requires code changes and redeployment.

#### 4. State Data Bag

`AIState.state_data` is an untyped dictionary holding:
- `path_requesting` (bool)
- `path_request_time` (float)
- `path_failed` (bool)
- `last_known_x/y` (floats)
- `path_destination` (tuple)
- `pursuit_repath` (bool)
- `last_repath_time` (float)

**Impact**: 
- No IDE autocomplete
- No type checking
- Easy to misspell keys
- Hard to reason about valid states

#### 5. Test Complexity

`test_predator_moving_target.py` requires:
- 6 different components on predator entity
- Manual physics body setup
- Mock physics system injection
- Manual frame stepping
- Manual transform updates

**Impact**: Writing new tests is expensive, so coverage suffers.

---

## Research: Industry Best Practices

### Hybrid BT + Utility AI

Modern game AI increasingly uses hybrid architectures:

> "Utility AI excels at goal selection while Behavior Trees excel at goal execution." 
> — Game AI Pro 3

The current system already uses this pattern:
- `UtilitySelector` chooses the goal
- Behavior trees execute the goal

**The problem isn't the pattern—it's the implementation.**

### Primitive Composition

The AntiFungal AI architecture (GDC 2015) demonstrated:
- Small, testable "atom" actions
- Composed into larger behaviors
- Easy to debug each layer

Our current actions are too coarse-grained.

### Data-Driven Design

From "The Sims" AI documentation:
- All tuning values in external files
- Designers can adjust without programmers
- A/B testing of parameters

We hardcode everything.

---

## Design Decisions

### Decision 1: Primitives Over Monoliths

**Alternative considered**: Refactor existing actions in place.

**Why rejected**: 
- Still tightly coupled
- Can't test navigation without movement
- Changes ripple unpredictably

**Chosen approach**: Extract primitives, compose them.

**Tradeoff**: More files, more indirection. But: each file is simple and testable.

### Decision 2: Typed Context Over Dictionary

**Alternative considered**: Add type hints to `state_data` dict.

**Why rejected**:
- Dict still allows arbitrary keys
- Runtime errors vs compile-time errors

**Chosen approach**: `ActionContext` dataclass with explicit fields.

**Tradeoff**: Less flexible for ad-hoc state. But: prevents entire category of bugs.

### Decision 3: Configuration Files Over Constants

**Alternative considered**: Class-level constants.

**Why rejected**:
- Still requires code changes
- Can't differ between builds (debug vs release)

**Chosen approach**: TOML configuration loaded at startup.

**Tradeoff**: Startup cost, file parsing. But: enables hot-reloading in future.

### Decision 4: Phased Migration Over Big Bang

**Alternative considered**: Write new system, switch entirely.

**Why rejected**:
- High risk of undetected regressions
- Long period without deliverables

**Chosen approach**: Four phases with working system at each milestone.

**Tradeoff**: Longer total timeline. But: reduces risk, allows course correction.

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Lines in `MoveToTarget.update()` | ~240 | < 50 (delegating to primitives) |
| Test setup lines | ~50 | < 20 |
| Configuration in code | 100% | < 10% (rest in TOML) |
| Duplicate action classes | 2 pairs | 0 |
| Type coverage of AI state | ~20% | 100% |

---

## Alternatives Not Chosen

### Full GOAP System

Goal-Oriented Action Planning would provide dynamic behavior sequencing.

**Why not**: 
- Overkill for current needs
- High implementation cost
- Current behavior tree structure sufficient for existing behaviors

**Future consideration**: If behavior complexity grows, GOAP could replace behavior trees.

### Machine Learning

ML could learn optimal action selection.

**Why not**:
- Unpredictable behavior
- Training data requirement
- Debugging difficulty

**Future consideration**: ML for tuning utility curves, not core decision-making.

### Event-Driven AI

Reactive AI responding to events rather than polling.

**Why not**:
- Major architecture change
- Current polling works adequately at current entity counts

**Future consideration**: If entity count grows significantly, event-driven could reduce CPU load.
