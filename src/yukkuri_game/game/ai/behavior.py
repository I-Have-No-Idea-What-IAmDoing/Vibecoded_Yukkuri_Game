"""
Legacy module for behavior tree logic.
This module now re-exports from the modular `yukkuri_game.game.ai.behaviors` package.
"""

from .behaviors import (
    Interact,
)

# Legacy alias if needed (though not found in search, adding just in case logic expects it)
Eat = Interact
# Add other re-exports as needed by legacy code/tests
