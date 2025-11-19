# Yukkuri Raising Game MVP

This project is a clean, maintainable, and extensible MVP of a modern "Yukkuri Raising Game," a reimagining of the classic fan game. It features a core engine focused on multi-agent care, utility AI behaviors, interactive placement, and a data-driven content layer.

## Features

-   **Multi-Yukkuri Simulation:** Watch multiple agents live and interact in a shared space.
-   **Utility AI:** Agents make their own decisions based on their needs (Hunger, Energy, etc.).
-   **Placement Mode:** Place furniture and other items in the world to care for your Yukkuris.
-   **Data-Driven:** All content (agents, items, actions) is loaded from JSON files, making the game easily moddable.
-   **Save/Load:** Save your progress and load it back up later.

## Getting Started

### Prerequisites

-   Python 3.11+
-   `pip` for installing dependencies

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd yukkuri-raising-game
    ```

2.  **Install the required packages:**
    A `Makefile` is provided for convenience.
    ```bash
    make install
    ```
    Alternatively, you can install the packages manually:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Game

-   **To run the game:**
    ```bash
    make run
    ```
    Or manually:
    ```bash
    python main.py
    ```

-   **To run the tests:**
    ```bash
    make test
    ```

## How to Play

-   **Toggle Modes:** Press the `P` key to switch between **Live Mode** and **Placement Mode**.
-   **Place Items:** In Placement Mode, click on an item in the right-hand inventory panel to select it. Then, click on the grid to place it.
-   **Save/Load:** Press `S` to save your game and `L` to load it.
-   **Take Screenshot:** Press `F12` to save a screenshot to the `screenshots/` directory.
