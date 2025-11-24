# Design Document: The "Narrative Ecology" System (Proposal 4)

## 1. Overview
This proposal synthesizes the simulation depth of Proposal 1, the social nuances of Proposal 2, and the performance pragmatism of Proposal 3. It rejects the extremes of "over-engineering" and "reductionism" in favor of a **Narrative Ecology** approach.

**Core Philosophy:**
1.  **Performance First:** Systems must scale to 100+ entities.
2.  **Readable Complexity:** Underlying math can be complex, but player feedback must be intuitive.
3.  **Memory that Matters:** Memories should fade, but trauma/bonds should leave scars.

## 2. Personality: The "Archetype + Variance" Model

We reject the raw "Big Five" (P1) and the simplistic "Tri-Axis" (P3). instead, we use a hybrid system.

### 2.1. The 4 Core Instincts (Float 0.0 - 1.0)
These are the biological hardwiring of the Yukkuri.
1.  **Survival (Self-Preservation):** Fear response, hunger priority, pain avoidance.
2.  **Social (Herd Impulse):** Desire for grouping, loneliness decay, empathy.
3.  **Assertion (Dominance):** Aggression, territoriality, demand for better food.
4.  **Cognition (Learning):** Pattern recognition, trap avoidance, tool use.

### 2.2. Traits as "Lenses"
Traits are not just stats. They are **Lenses** that filter perception and modify the Instincts.
*   *Example:* A `Predator` trait doesn't just `+0.5 Assertion`. It adds a **Behavioral Override**: "Small entities are Food, not Friends."
*   *Example:* A `Scum` trait inverts the Social instinct: "Gain pleasure from others' pain."

## 3. Emotional System: The "Hydraulic" Model

We avoid the expensive vector math of PAD (P1) and the static 2D graph of P3. We use a **Hydraulic Bucket System**.

### 3.1. The Buckets
Three buckets fill and drain over time.
1.  **Stress:** Fills with pain/fear. Drains with safety/sleep.
    *   *Overflow:* Panic/Frenzy.
2.  **Satisfaction:** Fills with food/play. Drains with time.
    *   *Empty:* Depression/Sluggishness.
3.  **Ego:** Fills with praise/winning. Drains with insults/defeat.
    *   *Overflow:* Arrogance/Rage. *Empty:* Submission.

### 3.2. Visual Feedback
*   *Stress Overflow* -> Shaking sprite, tears.
*   *Ego Overflow* -> "Puffing up" sprite animation.
*   *Low Satisfaction* -> Drooping accessories.

## 4. Memory: The "Weighted Highlight" System

We solve the memory bloat of P1 and the amnesia of P3 using a **Weighted Highlight** system.

### 4.1. Short-Term Buffer (The RAM)
Last 10 interactions. Used for immediate reaction logic. Cheap and fast.

### 4.2. Long-Term Impressions (The Hard Drive)
Instead of storing *events*, we store **Impressions** attached to specific Entity IDs.
```python
class Impression:
    entity_id: UUID
    affinity: float        # -100 to 100 (Like/Dislike)
    fear: float            # 0 to 100 (Threat assessment)
    respect: float         # 0 to 100 (Competence assessment)

    # The "Highlight Reel" - Max 3 items
    # Only the most emotionally impactful events replace these slots.
    key_memories: List[MemoryEvent]
```
*   *Logic:* If a new event happens, we compare its "Emotional Impact Score" to the existing 3 key memories. If it's higher, it overwrites the weakest one. This ensures they remember the *worst* beating and the *best* meal, but forget the mediocre daily hellos.

## 5. Social Propagation: The "Sector" System

We address the $O(N^2)$ problem of P2 using **Spatial Sectors**.

### 5.1. Sector-Based Broadcasting
The map is divided into large sectors (e.g., 4x4 grid).
*   **Visual Events:** Broadcast only to entities in the *same* or *adjacent* sectors who have Line-of-Sight.
*   **Auditory Events:** Broadcast to same sector (loud) or adjacent (very loud).

### 5.2. The Gossip Chain
Witnesses do not immediately update the victim's reputation. They add a "Gossip Packet" to their own outgoing queue.
*   *Interaction:* When Entity A talks to Entity B, they exchange top 3 Gossip Packets.
*   *Result:* Information spreads organically like a virus, rather than instantly via telepathy.

## 6. Architecture & Performance

### 6.1. The "Tick" Budget
AI processing is time-sliced.
*   **Frame 1-10:** Process Physics.
*   **Frame 11:** Update Emotions (Hydraulic model is cheap addition/subtraction).
*   **Frame 12-20:** Process 10% of Entity Decisions.
*   *Result:* 100+ entities run smoothly because complex decisions (Memory lookup) happen rarely.

### 6.2. Data Structures
*   `Instincts`: Struct of 4 floats.
*   `Hydraulics`: Struct of 3 floats.
*   `SocialGraph`: Dictionary `Map<EntityID, Impression>`.

## 7. Summary of Improvements
*   **Vs P1:** Removes obscure "Big Five" for clear "Instincts". Removes complex PAD vectors for "Buckets".
*   **Vs P2:** Defines the Memory/Witness system concretely with "Highlights" and "Sectors".
*   **Vs P3:** Retains the depth of long-term memory without infinite growth or arbitrary amnesia.
