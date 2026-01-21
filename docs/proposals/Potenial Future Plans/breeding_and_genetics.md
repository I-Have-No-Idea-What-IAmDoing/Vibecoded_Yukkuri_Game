# Proposal: Breeding & Genetics (Simplified)

## Overview
A straightforward breeding system where offspring inherit stats and personality from their parents with random variance, allowing for gradual improvement over generations without complex genetic micromanagement.

## 1. Inheritance Mechanics
Instead of simulating DNA alleles, we use a weighted average system with random drift.

### Stat Calculation
When a child is born, its base potential for stats (e.g., Max Health, Intelligence Cap) is calculated as:

`Base = (MotherStat + FatherStat) / 2`
`ChildStat = Base + Random(-Variance, +Variance)`

- **Variance**: Typically +/- 10%.
- **Mutation**: Rare small chance (5%) for a "Critical Success" (+20% bonus) or "Critical Failure" (-20% penalty).

### Personality Drift
Child personality values (Kindness, Bravery, etc.) are derived similarly.
- **Drift**: Personality tends to shift slightly from the parent's average, preventing clones.
- **Influence**: The mother's stress level during pregnancy may negatively impact the child's starting parameters.

## 2. Breeding Gameplay
How players interact with the system.

### The Process
1.  **Mating**: Two compatible Yukkuris influence each other to mate.
2.  **Pregnancy**: Mother gains `Pregnancy` status (Example duration: 3 days).
3.  **Birth**: 1-3 Koyukkuri spawn.

### Generations
We track the "Generation Count" of each Yukkuri.
- **Gen 1**: Starter/Shop Yukkuri.
- **Gen 2+**: Bred Yukkuris.
- **Benefit**: Higher generations often sell for more if their stats are high, as they represent invested time.

## 3. Variant Types
Rare sub-types of standard breeds (e.g., "Aquatic Marisa" is still a "Marisa").

### Mechanics
- **Definition**: Variants share the base Type ID but have a distinct `variant_id`.
- **Differences**:
    - **Visuals**: Palette swaps or unique accessories (e.g., Gills, Fins).
    - **Stats**: Unique modifiers (e.g., Aquatic = Water Tolerance ++).
- **Inheritance**:
    - If Parent is Variant: 40% chance to pass to child.
    - If Both Parents Variant: 80% chance.
    - **Mutation**: 1% chance for a normal Yukkuri to spawn as a specific Variant based on environment (e.g., bred in water pool).

## Technical Requirements

### 1. BreedingService
A simple service to handle the logic.

```python
class BreedingService:
    def create_offspring(self, mother_stats: YukkuriStats, father_stats: YukkuriStats) -> YukkuriStats:
        # 1. Average Stats
        base_int = (mother_stats.intelligence + father_stats.intelligence) / 2.0
        
        # 2. Apply Variance (e.g., +/- 0.1)
        variance = rng.uniform(-0.1, 0.1)
        
        # 3. Create Child Stats
        child_stats = YukkuriStats(
            intelligence = clamp(base_int + variance, 0.5, 2.0),
            generation = max(mother_stats.badges, father_stats.badges) + 1 # simplistic gen tracking
        )
        return child_stats
```

### 2. Data Integration
- No complex component needed.
- `generation` field added to `YukkuriStats`.
- `variant_id` field added to `YukkuriStats` (Default: "standard").
