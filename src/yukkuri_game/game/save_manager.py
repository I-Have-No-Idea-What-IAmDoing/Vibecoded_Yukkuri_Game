"""
Save Manager Service.

Handles serialization and deserialization of the game state,
including both ECS level data and global economy/time data.
"""

import json
import os
import sqlite3
from typing import TYPE_CHECKING, Any

from loguru import logger

from ..engine.ecs import World
from ..engine.serializer import WorldSerializer
from .components import YukkuriStats
from yukkuri_game.engine.components import Transform
from .services import EconomyService
from yukkuri_game.engine.services.time_service import TimeService
from .ai.navigation_service import NavigationService
from .skill_service import SkillService
from .systems.physics_reconstruction import reconstruct_physics

if TYPE_CHECKING:
    from yukkuri_game.engine.camera import Camera


class SaveManager:
    """
    Service responsible for saving and loading the game state.

    Attributes:
        world (World): The ECS World.
        serializer (WorldSerializer): The ECS component serializer.
        economy_service (EconomyService): Service for global money.
        time_service (TimeService): Service for global time.
    """

    def __init__(self, world: World, component_types: list[type[Any]]) -> None:
        """
        Initializes the SaveManager.

        Args:
            world (World): The ECS world.
            component_types (list[type[Any]]): Component types to serialize.
        """
        self.world = world
        self.serializer = WorldSerializer(world, component_types)

        # Cache required services
        self.economy_service = world.services.get(EconomyService)
        self.time_service = world.services.get(TimeService)

    def save_game(self, filepath: str) -> None:
        """
        Saves the game state (Level + Global) to an SQLite file.

        Args:
            filepath (str): The base filepath for saving.
        """
        base_path, _ = os.path.splitext(filepath)
        sqlite_path = base_path + ".sqlite"

        # Save Global Data
        global_data = {
            "money": self.economy_service.money,
            "time": self.time_service.time_elapsed,
        }

        conn = sqlite3.connect(sqlite_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS global_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            cursor.execute(
                "INSERT OR REPLACE INTO global_state (key, value) VALUES (?, ?)",
                ("global_data", json.dumps(global_data)),
            )

            # Save Level Data
            self.serializer.save_to_sqlite(conn)
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Game saved to {sqlite_path}")

    def load_game(self, filepath: str, camera: "Camera | None" = None) -> None:
        """
        Loads the game world from an SQLite file.

        Args:
            filepath (str): The base filepath to load from.
            camera (Camera | None): The camera to reset upon loading.
        """
        base_path, _ = os.path.splitext(filepath)
        sqlite_path = base_path + ".sqlite"

        if not os.path.exists(sqlite_path):
            logger.error(f"Save file not found: {sqlite_path}")
            return

        # Clear World
        self.world.clear_database()
        
        if camera:
            camera.clear()

        # Reset Navigation Service
        nav_service = self.world.services.try_get(NavigationService)
        if nav_service:
            nav_service.reset()

        conn = sqlite3.connect(sqlite_path)
        try:
            cursor = conn.cursor()

            # Load Global Data
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='global_state'"
            )
            if cursor.fetchone():
                cursor.execute("SELECT value FROM global_state WHERE key='global_data'")
                row = cursor.fetchone()
                if row:
                    global_data = json.loads(row[0])
                    self.economy_service.set_money(global_data.get("money", 0))
                    self.time_service.time_elapsed = global_data.get("time", 0.0)

            # Load Level Data
            self.serializer.load_from_sqlite(conn)
        finally:
            conn.close()

        # Reconstruct physics bodies
        reconstruct_physics(self.world)

        # Migrate Skills
        skill_service = self.world.services.try_get(SkillService)
        if skill_service:
            for ent, (_, _) in self.world.get_components_tuple(
                YukkuriStats, Transform
            ):
                skill_service.initialize_skills(ent)

        logger.info("World loaded.")
