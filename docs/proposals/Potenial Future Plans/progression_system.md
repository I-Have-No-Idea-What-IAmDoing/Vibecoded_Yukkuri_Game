# Proposal: Goals & Progression System

## Overview
To provide players with long-term goals and a sense of accomplishment, we will implement a comprehensive Achievement system. This system allows players to track their milestones and completion status.

## 1. Achievements & Milestones
A system to track player milestones for the satisfaction of completion.

### Implementation Details
- **Data Structure**: `data/achievements.toml` defining criteria (e.g., `type="count_yukkuris"`, `target=10`).
- **UI**: A new tab in the HUD to view progress, potentially with a "Trophy Case" visual.
- **Philosophy**: Achievements are "for their own sake" - a record of the player's dedication and exploration of the game's mechanics.

### Examples
- **"Yukkuri Rancher"**: Raise 10 Yukkuris to adulthood.
- **"Big Spender"**: Spend over $5,000 in the shop.
- **"Badge Collector"**: Have 5 Yukkuris with max badges.
- **"Generational Wealth"**: Have a Yukkuri reach Generation 5.
- **"Completionist"**: Unlock every badge type at least once.

## Technical Architecture

### 1. Data Models
We will define strict data structures to ensure type safety and ease of serialization.

```python
@dataclass
class AchievementCriteria:
    condition: str  # simpleeval expression, e.g., "money_earned >= 1000"

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    criteria: List[AchievementCriteria]
    reward: Dict[str, float]
    is_hidden: bool = False
```

### 2. The ProgressionService
A new service class `ProgressionService` will act as the central manager.

- **Responsibility**:
    - Load definitions from `data/achievements.toml`.
    - Maintain runtime state of `ProgressData`.
    - **Integration**: Use `ConditionEvaluator` to check `AchievementCriteria.condition`.

#### Evaluation Context
The `ProgressionService` must build a context for the evaluator containing tracking data.

```python
# In ProgressionService
def check_achievements(self):
    # Build context from internal counters
    context = {
        "money_earned": self.progress.money_earned,
        "yukkuris_raised": self.progress.yukkuris_raised,
        "badges_collected": self.progress.badges_collected,
        # ... other tracked stats
    }
    
    for ach in self.achievements:
        if not ach.unlocked:
            # Check all criteria using the existing evaluator system
            if all(self.evaluator.evaluate(c.condition, context) for c in ach.criteria):
                self.unlock(ach)
```

#### Event Integration
The service will listen to granular events to minimize polling.

```python
# In ProgressionService.__init__
self.event_bus.subscribe(YukkuriSoldEvent, self._on_yukkuri_sold)
self.event_bus.subscribe(ItemBoughtEvent, self._on_item_bought)

def _on_yukkuri_sold(self, event: YukkuriSoldEvent):
    self.progress.total_sold += 1
    self.progress.money_earned += event.value
    self._check_unlocks("economy")
```

### 3. Persistence Layer (`PersistenceService`)
The existing `PersistenceService` (formerly `save_system.py`) needs an update to serialize the new data.

- **Schema Update**:
    ```json
    {
      "version": "1.0",
      "resources": { ... },
      "progression": {
        "unlocked_achievements": ["first_sale", "rancher_novice"],
        "counters": {
            "total_money_earned": 5050,
            "yukkuris_born": 12
        }
      }
    }
    ```
- **Action**: Add `ProgressionService` to the `save()` and `load()` chains in `GameLoop` or `Loader`.

### 4. Notification System
We need a visual feedback queue for when achievements are triggered.

- **UI Component**: `AchievementPopup` (slide-in notification).
- **Audio**: Play a distinct "jingle" upon unlock.
