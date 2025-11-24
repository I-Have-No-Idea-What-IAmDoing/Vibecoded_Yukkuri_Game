# Critique of Proposal 2: Enhanced Personality & Relationship System

## 1. General Assessment: Vague & Incomplete
While Proposal 2 is less egregiously over-engineered than Proposal 1, it suffers from being under-specified. It reads more like a "What if?" brainstorm than a concrete design document. It lacks the technical depth required for implementation, leaving too many critical decisions to the developer's whim during coding.

## 2. Specific Flaws

### 2.1. Vector-Based Personality
*   **Arbitrary Dimensions:** The choice of dimensions (Curiosity, Aggression, Social, Rationality) feels random. Why these four? How do they interact?
*   **Trait Confusion:** The proposal says Traits act as "modifiers" to these vectors. This creates a dual-system problem: Is a Yukkuri aggressive because of its `Aggression` float or its `Predator` trait? Managing two layers of personality definition invites conflict and bugs.

### 2.2. PAD Model (Again)
*   **Implementation Gaps:** Like Proposal 1, this suggests PAD but fails to define the decay logic, the specific impulse values for interactions, or how it integrates with the existing AI loop. "Interactions now impart Delta-P..." is easy to say, but balancing those deltas is the entire game.
*   **Visual Feedback:** The suggestion to use "color tinting" for mood visualization is lazy UX design. Players shouldn't need to decipher RGB shifts to know if their pet is angry.

### 2.3. Memory System
*   **Semantic Vector Confusion:** "Long-Term Memory" is described as a "Sentiment Vector" (Affinity, Respect, Trust). This is just *stats*. Calling it "Semantic Memory" obscures the fact that it's just a set of 3 float variables.
*   **Consolidation Logic Holes:** "Repeated negative events lower Affinity." How many? How fast? The logic is entirely hand-waved.
*   **Locking Trauma:** The idea that high-impact trauma is "locked" suggests a permanent state change, but the mechanism for "unlocking" or healing is ignored. This leads to broken game states where units are permanently stuck.

### 2.4. Social Dynamics (Witness System)
*   **The Radius Problem:** "Broadcast to entities within a radius R." This is a classic $O(N^2)$ neighbor search problem. Without spatial partitioning (quadtrees/grids), this will kill performance in dense colonies.
*   **Schadenfreude Logic:** The logic "C's opinion of A might increase (if C hates B)" is simplistic. It ignores context. If A kills B (my enemy) but does it in a horrifying way, I might still fear/hate A. The proposal simplifies social dynamics to simple arithmetic, which rarely produces believable behavior.

## 3. Implementation Plan (tasks.md)
*   **Phase 1 Bloat:** "Refactor Personality" and "Refactor RelationshipData" are massive tasks lumped into single checkboxes.
*   **Missing Tests:** Unlike Proposal 1, this plan completely ignores testing. There is no mention of unit tests, regression tests, or how to verify these complex interactions.
*   **Migration Hand-waving:** "Convert existing entities... to approximate PAD vectors." How? What is the mapping? This is a data migration nightmare left undefined.

## 4. Verdict
**Reject.** This proposal is a half-baked sketch. It identifies the right problems (lack of depth, need for memory) but offers solutions that are both technically vague and potentially performant-heavy (radius broadcasting) without addressing the implementation details.
