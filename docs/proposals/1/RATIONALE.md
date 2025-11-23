# Rationale for Personality & Relationship System 2.0

## 1. Limitations of the Current System

The current implementation (`SocialSystem.py`, `yukkuri_components.py`) serves as a functional MVP but suffers from several design constraints that limit gameplay depth:

*   **Static Moods:** Moods are hardcoded strings ("HAPPY", "NEUTRAL"). Transitions are binary and lack nuance. A Yukkuri is either "FURIOUS" or not, with no gradient for "Annoyed" or "Frustrated".
*   **Linear Decay:** Relationships decay linearly over time. This is computationally cheap but unrealistic. Real relationships are defined by key moments (memories), not just a generic "fading" of affinity.
*   **Shallow Memory:** The `memories` list is a simple circular buffer of the last 20 interactions. It doesn't distinguish between "Ate a cookie" (trivial) and "Betrayed by brother" (life-defining).
*   **Lack of Individuality:** While "Traits" exist, they function mostly as boolean flags. Two "Rude" Yukkuris behave identically. There is no underlying personality matrix to differentiate them.

## 2. The "Simulationist" Philosophy

The proposed design shifts the focus from **Gamey Stats** (filling bars) to **Simulationist Drama** (emergent stories).

*   **Emergent Behavior:** By interacting the *Drives* (Needs) with *Personality Dimensions* and *Emotional State*, complex behaviors emerge naturally.
    *   *Example:* A highly Neurotic (Low Stress Tolerance) Yukkuri who is hungry (Drive) might tantrum (High Arousal/Low Pleasure) rather than search for food, whereas a Conscientious one would diligently forage.
*   **Story Generation:** The new Memory system means Yukkuris hold grudges or form deep bonds based on specific events. This allows players to tell stories: "Reimu hates Marisa because Marisa stole her sweet-sweet in cycle 5."

## 3. Comparative Analysis

### vs. RimWorld
*   **RimWorld** uses a "Social Log" where every interaction has a chance to form a "Opinion" modifier that lasts for set durations (e.g., "Chitchat +5", "Insulted -15").
*   **Our Proposal** adopts this specific "Event -> Modifier" approach for the Relationship system, replacing the fluid "Affinity" bar with a calculated sum of memories.

### vs. The Sims
*   **The Sims** uses a "Need-based" AI where actions are advertised as solving needs (e.g., Toilet: Bladder +100).
*   **Our Proposal** adopts this for the "Drives" system. Social interactions will advertise fulfillment of the "Social" drive, filtered by Personality compatibility.

### vs. Dwarf Fortress
*   **Dwarf Fortress** simulates extreme granularity, where a unit's values change over decades.
*   **Our Proposal** simplifies this. We don't need to simulate decades, but the concept of "Personality changing via Trauma" (Core Memories) is adapted here.

## 4. Expected Impact

*   **Gameplay:** Players will care more about individual Yukkuris because their behavior is unique and consistent with their history.
*   **Performance:** Paradoxically, the new system may be more performant in some areas. Instead of ticking/decaying every relationship every frame, "Opinions" are cached and only recalculated when a new Memory is added or expires.
*   **Extensibility:** The PAD emotion model allows adding infinite "Mood" labels without changing the underlying logic—just map a new region of the 3D vector space to a name.
