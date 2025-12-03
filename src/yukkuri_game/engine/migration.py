"""
Migration Registry Module.
"""

from typing import Dict, Any, Callable, Type, List, Tuple
from loguru import logger

MigrationFunc = Callable[[Dict[str, Any]], Dict[str, Any]]


class MigrationRegistry:
    """
    Registry for component migration functions.
    Handles upgrading component data from older versions to newer ones.
    """

    _migrations: Dict[str, List[Tuple[int, int, MigrationFunc]]] = {}

    @classmethod
    def register(
        cls,
        component_class: Type,
        from_version: int,
        to_version: int,
        func: MigrationFunc,
    ) -> None:
        """
        Registers a migration function for a component.

        Args:
            component_class (Type): The component class.
            from_version (int): The version to migrate from.
            to_version (int): The version to migrate to.
            func (MigrationFunc): The function that transforms the data dict.
        """
        name = component_class.__name__
        if name not in cls._migrations:
            cls._migrations[name] = []
        cls._migrations[name].append((from_version, to_version, func))
        # Sort by from_version to ensure sequential application
        cls._migrations[name].sort(key=lambda x: x[0])

    @classmethod
    def migrate(
        cls,
        component_name: str,
        data: Dict[str, Any],
        current_version: int,
        target_version: int,
    ) -> Dict[str, Any]:
        """
        Applies migrations to bring data from current_version to target_version.

        Args:
            component_name (str): The name of the component.
            data (Dict[str, Any]): The raw data dictionary.
            current_version (int): The version of the data.
            target_version (int): The target version (usually component class version).

        Returns:
            Dict[str, Any]: The migrated data.
        """
        if current_version >= target_version:
            return data

        if component_name not in cls._migrations:
            logger.warning(
                f"No migrations found for {component_name} (v{current_version} -> v{target_version})"
            )
            return data

        migrations = cls._migrations[component_name]

        for from_v, to_v, func in migrations:
            if from_v == current_version:
                logger.info(f"Migrating {component_name} from v{from_v} to v{to_v}")
                try:
                    data = func(data)
                    current_version = to_v
                except Exception as e:
                    logger.error(
                        f"Migration failed for {component_name} v{from_v}->v{to_v}: {e}"
                    )
                    raise e

            if current_version >= target_version:
                break

        if current_version < target_version:
            logger.warning(
                f"Could not fully migrate {component_name}. Stopped at v{current_version}, target v{target_version}"
            )

        return data
