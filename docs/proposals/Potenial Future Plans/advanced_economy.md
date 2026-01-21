# Proposal: Advanced Economy

## Overview
Add strategic depth to the economic layer of the game, requiring players to manage expenses and relationships, not just maximize sales.

## 1. Reputation System
The player's standing with the Yukkuri-buying community affects prices and opportunities.

### Mechanics
- **Reputation (Rep)**: A float value from `-100.0` to `+100.0`. Starts at `0.0`.
- **Tiers**:
    - **Scammer** (<-50): Prices x0.5. No special orders.
    - **Neutral** (-50 to 50): Prices x1.0. Standard customers.
    - **Trustworthy** (>50): Prices x1.2. High-value orders.
    - **Legendary** (>90): Prices x1.5. Rare item access.

### Formula
Price Multiplier = $1.0 + (Rep / 200.0)$
*(e.g., +100 Rep = 1.0 + 0.5 = 1.5x Multiplier)*

### Implementation: EconomyService
Refactor `EconomyService` to track `reputation`.
```python
def modify_reputation(self, amount: float, reason: str):
    self.reputation = clamp(self.reputation + amount, -100, 100)
    self.event_bus.publish(ReputationChangedEvent(self.reputation, reason))
```

## 2. Customer Orders
Specific requests from buyers that provide focused goals.

### Data Structure
Define orders in a type-safe way:
```python
@dataclass
class CustomerOrder:
    id: str
    deadline: float  # Game time
    description: str
    requirements: str  # simpleeval condition: "has_trait('Rare') and intelligence > 1.2"
    reward_money: int
    reward_rep: float
    penalty_rep: float
```

### Workflow
1.  **Generation**: Daily chance to spawn an order based on current Rep.
2.  **Acceptance**: Player accepts via UI. Order added to `EconomyService.active_orders`.
3.  **Submission**: Player drags a Yukkuri to the "Delivery Box".
4.  **Validation**: System checks Yukkuri against `requirements`.
    - *Pass*: Money + Rep gained. Yukkuri deleted (sold).
    - *Fail*: Yukkuri returned.
5.  **Expiry**: If deadline passes, `penalty_rep` is applied.

## 3. Resource Management & Decay
Item maintenance to prevent unlimited resource accumulation.

### New Component: `Durability`
```python
@dataclass(slots=True)
class Durability(Component):
    current: float = 100.0
    max_value: float = 100.0
    decay_rate: float = 0.1  # Loss per game hour
    destroy_on_zero: bool = True
```

### Implementation Details
- **DecaySystem**: Iterates all entities with `Durability`.
    - Subtracts `decay_rate * dt`.
    - Updates visual state (e.g., "Tattered Bed").
    - If <= 0: Triggers `destroy_entity` or disables function.
- **Consumption**: Interacting with items (Sleeping, Playing) accelerates decay.
- **Maintenance**: New item "Repair Kit" restores durability.

## Technical Requirements
- **EconomyService**: Add `reputation` state and `order_manager`.
- **ItemStats**: No change needed, `Durability` is a separate component.
- **UI**: New "Orders" tab in the Shop menu.
