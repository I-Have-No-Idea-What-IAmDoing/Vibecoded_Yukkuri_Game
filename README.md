# Vibecoded_Yukkuri_Game

## **Core Objectives**
1. Build the **main game engine** using Python and Pygame-ce and any other modern libraries as needed.
2. Implement clean, modular architecture that supports future expansion to web-based platforms.
3. Use placeholder assets and mock data files (JSON/YAML/TOML) for testing. No final art or production data is required.

---

## **Core Gameplay Loop**
* **Raise**: Players manage a "Yukkurrium" (Yukkuri Tank) where multiple Yukkuris coexist and interact with items.
* **Care & Growth**: Yukkuris autonomously manage needs (Hunger, Happiness, Health), grow through stages, and exhibit basic social/environmental interactions.
* **Train**: Include simple mini-game stubs for training Yukkuris to earn badges that increase sell value.
* **Sell**: Implement logic to sell a Yukkuri based on its **Quality Score**, increasing in-game currency.
* **Reinvest**: Allow players to use currency to buy better items, food, and facilities to improve raising efficiency.

---

## **Technology Stack**
* **Language**: Python 3.11+
* **Framework**: Pygame-ce for rendering and pygame-gui for UI
* **Data**: External TOML or strict YAML files for all configurations and AI parameters
* **Architecture**: Component-Entity-System (ECS)-inspired design for scalability
* Project should use UV and pyproject.toml as the main build tool
---

## **Required Features**
### **Yukkuri & State Management**
* Implement a central system to manage 25+ independent Yukkuri entities.
* Each Yukkuri tracks: 'Name', 'Health`, `Hunger`, `Happiness`, `Cleanliness`, `Age` (mapped to `GrowthStage: Baby, Child, Adult`), and `QualityScore` (a calculated value).
* Enable basic peer-to-peer and environment interactions (e.g., eating food, talking).

### **Utility AI System**
* Implement a **Utility-Based AI (UBI)** for autonomous decision-making.
* Define modular actions (Eat, Sleep, Talk, Breed) with utility calculations.
* Load **Action Sets**, **Considerations**, and **Utility Curves** from external data files.
* Within the `GameLoop`, the UBI must efficiently iterate over 25+ Yukkuri, calculate the aggregate utility for all available actions, and execute the highest-scoring action.
* Employ A* pathfinding to guide the Yukkuri's movement toward items required to complete actions.

### **Data-Driven Design**
* All game data and AI parameters must be externalized in TOML/YAML.
* Validate data during loading and handle errors gracefully.

### **Customization**
* Implement a basic 2D Yukkurrium simulation space.
* Allow modular placement and removal of items (food, beds) and define interactions.
* Players should be able to pan and zoom the 2D Yukkurrium simulation.
* Players should be able to control the speed of the simulation

### Game Economy & Persistence

* Implement the logic for calculating the `QualityScore` based on the Yukkuri's current and past states (e.g., high average `Happiness`, successful completion of `Train` milestones/badges).
* Implement a function that, when triggered, removes the selected Yukkuri from the simulation and adds currency to the player's balance equal to the calculated `QualityScore`.
* Abstractly include a `Badge` counter/list on the `Yukkuri` entity. A placeholder UI button/mini-game that, when activated, increases a Yukkuri's `Badge` count, which directly contributes to its `QualityScore`.
* Implement functions for `SaveGame()` and `LoadGame()` that correctly handle the current in-game money, time, and the complete state (position, stats, badges) of all active `Yukkuri` and placed `Item` entities.

---

## **MVP Deliverables**
1. Classes for `Yukkuri`, `Item`, `Yukkurrium`, `UtilityAIEngine`, and `GameLoop`.
2. Basic Pygame UI for:
   * Viewing Yukkuri stats
   * Placing/removing items
   * Selling Yukkuris
   * The current time and money
3. System for updating and persisting game state (time, money, entity status).
4. Placeholder data files for:
   * 2 Yukkuri types
   * 3–4 item types
   * 5 AI actions with full utility curve definitions
5. Logic for saving/loading game state.

---

## **Documentation**
* Provide setup instructions for running the game locally.
* Include clear steps for adding:
   * A new Yukkuri type
   * A new item
   * A new AI action
by modifying external data files.

---

**Key Principles**: Clean architecture, modularity, data-driven design, and extensibility.

Your output should include:
* A complete, runnable Python project with placeholder assets.
* Well-commented code following best practices.
* Example TOML/YAML files for entities and AI definitions.

**Failure Conditions:** The MVP fails if the Yukkuri entities do not autonomously select and execute actions based on their current needs (Utility Score calculation) and environmental items, or if a new action/item cannot be added without modifying the Python source code.
