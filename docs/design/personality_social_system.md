# Personality & Social System

## Overview
The "Clear-Cut" Personality & Social System introduces depth to Yukkuri behavior through structured personality axes, emotional states, memory management, and social gossip.

## 1. Personality: The Quad-Axis Model
Yukkuris have a 4-Axis integer personality system (-100 to +100):
1.  **Kindness:** Willingness to share/help vs harm (Gesu <-> Nice).
2.  **Energy:** Action frequency/speed (Lazy <-> Hyper).
3.  **Bravery:** Fight/flight threshold (Coward <-> Brave).
4.  **Greed:** Hoarding/resource sharing (Generous <-> Greedy).

### Personality Drift
Personality values naturally drift towards a "Base" value (genetic + traits) over time. This rate is configurable in `rules.toml` via `personality_drift_rate`.

## 2. Emotional State
Replaces simple happiness/stress stats with a dedicated component.
- **Happiness (-100 to 100):** Decays towards 0 (Contentment).
- **Stress (0 to 100):** Decays towards 0. High stress triggers panic/rage.

## 3. Memory: The "Headline" System
Relationships store memories as **Headlines** in two buffers:
- **Trivial Buffer:** Short-term, low-impact events (size 25).
- **Core Buffer:** Long-term, high-impact events (size 35).

### Locking
Important memories can be **Locked**, preventing them from being overwritten by trivial events.
The importance threshold for Core memories is configurable via `memory_importance_threshold`.

## 4. Gossip System
Information spreads via gossip exchange during conversation and witnessing events.
- **Witnessing:** Entities within Visual (300px) or Auditory (600px) range generate gossip packets.
- **Exchange:** Entities exchange top gossip packets when interacting.
- **Config:** Max gossip queue length is configurable via `max_gossip_length`.

## Configuration (`data/rules.toml`)
```toml
[stat_decay]
personality_drift_rate = 0.1

[social]
memory_importance_threshold = 50.0
max_gossip_length = 10
```
