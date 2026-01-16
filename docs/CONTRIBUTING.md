# Contributing to Yukkuri Raising Game

Thank you for your interest in contributing to the Yukkuri Raising Game! We welcome contributions from everyone. This document provides guidelines and instructions for contributing to the project.

## Getting Started

1.  **Fork the repository**: Click the "Fork" button on the top right of the GitHub page.
2.  **Clone your fork**:
    ```bash
    git clone https://github.com/yourusername/yukkuri-raising-game.git
    cd yukkuri-raising-game
    ```
3.  **Install dependencies**:
    We use `uv` for dependency management.
    ```bash
    uv sync
    ```

## Development Workflow

1.  **Create a new branch**:
    ```bash
    git checkout -b feature/my-new-feature
    ```
    or
    ```bash
    git checkout -b fix/issue-number
    ```
2.  **Make your changes**: Implement your feature or fix.
3.  **Run tests**: Ensure that existing tests pass and add new tests for your changes.
    ```bash
    uv run pytest
    ```
4.  **Linting and Type Checking**:
    The project uses `mypy` for static type checking. Ensure your code passes type checks.
    ```bash
    uv run mypy src/
    ```
5.  **Commit your changes**: Write clear and concise commit messages.
    ```bash
    git commit -m "Add feature X"
    ```
6.  **Push to your fork**:
    ```bash
    git push origin feature/my-new-feature
    ```
7.  **Open a Pull Request**: Go to the original repository and open a Pull Request from your fork.

## Code Style

-   **Python Version**: We use Python 3.11+.
-   **Docstrings**: Use Google Style Python Docstrings for all public modules, functions, classes, and methods.
-   **Type Hinting**: Use type hints for function arguments and return values. This is enforced by `mypy`.
-   **Formatting**: Try to follow PEP 8 guidelines.

### Example Docstring

```python
def calculate_velocity(distance: float, time: float) -> float:
    """Calculates velocity based on distance and time.

    Args:
        distance (float): The distance traveled.
        time (float): The time taken.

    Returns:
        float: The calculated velocity.

    Raises:
        ValueError: If time is zero.
    """
    if time == 0:
        raise ValueError("Time cannot be zero.")
    return distance / time
```

## Adding New Content

The game is data-driven. You can add new content by modifying the TOML files in the `data/` directory. See [Data Driven Design](DATA_DRIVEN_DESIGN.md) for more details.

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub. Provide as much detail as possible, including steps to reproduce the bug or a clear description of the feature.

## License

By contributing, you agree that your contributions will be licensed under the project's license (see `LICENSE` file).
