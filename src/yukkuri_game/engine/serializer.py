"""
World Serialization Module.

Handles save/load of ECS world state using MessagePack binary format.
Uses a two-pass approach to resolve entity reference remapping:

Two-Pass Algorithm:
1. **Create Pass**: Deserialize all entities and components, building a
   mapping of old_entity_id -> new_entity_id. EntityID fields temporarily
   hold stale (old) values.

2. **Resolve Pass**: Scan all component fields for EntityID type hints.
   Remap any EntityID values using the old->new mapping. Mark dangling
   references (entities that weren't saved) as -1.

This approach handles circular dependencies where Entity A references
Entity B and vice versa, avoiding issues with creation order.

Supported Reference Types:
- EntityID (scalar)
- Optional[EntityID]
- list[EntityID], set[EntityID]
- dict[EntityID, Any] (key remapping)
"""

import types
import typing
from collections.abc import Iterable
from typing import (
    Any,
    get_args,
    get_origin,
)

import msgspec
from loguru import logger

from .ecs import World
from .migration import MigrationRegistry
from .types import EntityID


class WorldSerializer:
    """
    Serializes and deserializes ECS world state.

    Uses msgspec for efficient binary encoding and supports:
    - Component versioning and migration
    - Entity ID remapping on load
    - Circular reference handling via two-pass resolution

    Attributes:
        world (World): The ECS World to serialize/deserialize.
        component_map (dict[str, type[Any]]): Mapping of component names to types.
        _persistable_type (type[Any] | None): The Persistable component type.
        _stable_id_type (type[Any] | None): The StableIDComponent type.
    """

    def __init__(self, world: World, component_types: Iterable[type[Any]]):
        """
        Initializes the WorldSerializer.

        Args:
            world (World): The ECS World to serialize/deserialize.
            component_types (Iterable[type[Any]]): Component types to include in serialization.
        """
        self.world = world
        self.component_map = {c.__name__: c for c in component_types}
        self._persistable_type = self.component_map.get("Persistable")
        self._stable_id_type = self.component_map.get("StableIDComponent")

    def serialize_entity(self, entity: int) -> dict[str, Any] | None:
        """
        Serializes a single entity.

        Args:
            entity (int): The entity ID to serialize.

        Returns:
            dict[str, Any] | None: A dict containing 'entity_id', 'stable_id', 'components',
            or None if the entity is not persistable.
        """
        if not self._persistable_type or not self.world.has_component(
            entity, self._persistable_type
        ):
            return None

        stable_id = None
        if self._stable_id_type:
            stable_id_comp = self.world.try_get_component(entity, self._stable_id_type)
            stable_id = stable_id_comp.id if stable_id_comp else None

        components_data = {}
        all_components = self.world.get_all_components(entity)

        for component in all_components:
            component_type = type(component)
            # Skip components that shouldn't be serialized
            if component_type.__name__ == "PhysicsBody":
                continue

            if self._stable_id_type and component_type == self._stable_id_type:
                continue

            try:
                if hasattr(component, "__dataclass_fields__") or isinstance(
                    component, msgspec.Struct
                ):
                    decoded = msgspec.to_builtins(component)
                    if hasattr(component_type, "_version_"):
                        decoded["_version_"] = getattr(
                            component_type, "_version_"
                        )  # Add version.
                    components_data[component_type.__name__] = decoded
                else:
                    pass  # Skip non-serializable.
            except Exception as e:
                logger.warning(
                    f"Failed to serialize component {component_type.__name__} for entity {entity}: {e}"
                )

        return {
            "entity_id": entity,
            "stable_id": stable_id,
            "components": components_data,
        }

    def get_persistable_entities_data(self) -> list[dict[str, Any]]:
        """
        Returns a list of serialized data for all persistable entities.

        Returns:
            list[dict[str, Any]]: A list of serialized entity data dictionaries.
        """
        if not self._persistable_type:
            logger.warning("Persistable component type not registered. Cannot save.")
            return []

        entities_data = []
        for entity, _ in self.world.get_components(self._persistable_type).items():
            data = self.serialize_entity(entity)
            if data:
                entities_data.append(data)
        return entities_data

    def save_to_file(self, filepath: str) -> None:
        """
        Saves all persistable entities to a file using MessagePack.

        Args:
            filepath (str): The path to the file to save to.
        """
        entities_data = self.get_persistable_entities_data()
        with open(filepath, "wb") as f:
            f.write(msgspec.msgpack.encode(entities_data))
        logger.info(f"Saved {len(entities_data)} entities to {filepath}")

    def load_from_file(self, filepath: str) -> None:
        """
        Loads entities from a file using MessagePack with two-pass reference resolution.

        Args:
            filepath (str): The path to the file to load from.
        """
        try:
            with open(filepath, "rb") as f:
                data = f.read()
                entities_data = msgspec.msgpack.decode(data)
        except FileNotFoundError:
            logger.error(f"Save file {filepath} not found.")
            return

        self.load_from_data(entities_data)

    def load_from_data(self, entities_data: list[dict[str, Any]]) -> None:
        """
        Loads entities from a list of entity data dicts with two-pass reference resolution.

        This method uses a two-pass approach to handle circular dependencies and ID remapping:
        1. Create all entities and components first, building a map of old_id -> new_id.
        2. Iterate through all created components and resolve any EntityID fields to the new IDs.

        Args:
            entities_data (list[dict[str, Any]]): A list of serialized entity data dictionaries.
        """
        if not entities_data:
            return

        # Pass 1: Create entities with stale EntityID references.
        id_map: dict[int, int] = {}  # old_id -> new_id
        max_stable_id = 0

        for entity_data in entities_data:
            old_id = entity_data.get("entity_id")
            stable_id = entity_data.get("stable_id")
            components_data = entity_data.get("components", {})

            # Create new entity
            new_entity = self.world.create_entity()
            if old_id is not None:
                id_map[old_id] = new_entity

            # Add StableID if exists
            if stable_id is not None and self._stable_id_type:
                self.world.add_component(new_entity, self._stable_id_type(id=stable_id))
                if isinstance(stable_id, int):
                    max_stable_id = max(max_stable_id, stable_id)

            for comp_name, comp_data in components_data.items():
                comp_class = self.component_map.get(comp_name)
                if comp_class:
                    try:
                        # Check migration
                        saved_version = comp_data.pop("_version_", 0)
                        target_version = getattr(comp_class, "_version_", 0)

                        if saved_version < target_version:
                            comp_data = MigrationRegistry.migrate(
                                comp_name, comp_data, saved_version, target_version
                            )

                        component = msgspec.convert(comp_data, comp_class)
                        self.world.add_component(new_entity, component)
                    except Exception as e:
                        logger.warning(
                            f"Failed to deserialize component {comp_name}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.warning(f"Unknown component type: {comp_name}")

        if hasattr(self.world, "set_next_stable_id"):
            self.world.set_next_stable_id(max_stable_id + 1)  # Avoid ID collision.

        # Pass 2: Remap EntityID references using id_map.
        for new_entity in id_map.values():
            all_components = self.world.get_all_components(new_entity)
            for component in all_components:
                try:
                    type_hints = typing.get_type_hints(component)
                except (TypeError, NameError):
                    continue

                for field_name, field_type in type_hints.items():
                    if not hasattr(component, field_name):
                        continue

                    val = getattr(component, field_name)
                    if val is None:
                        continue

                    if self._is_entity_ref(field_type):
                        if isinstance(val, int) and not isinstance(val, bool):
                            if val in id_map:
                                setattr(component, field_name, EntityID(id_map[val]))
                            elif val > 0:
                                setattr(
                                    component, field_name, EntityID(-1)
                                )  # Dangling.
                        else:
                            pass
                    elif field_name.endswith("_id") and field_type is int:
                        # Generic int field that looks like an ID but isn't typed as EntityID
                        # This won't be remapped!
                        logger.warning(
                            f"Field '{field_name}' in component '{type(component).__name__}' for entity {new_entity} "
                            f"is typed as 'int' but looks like an ID. It will NOT be remapped! "
                            f"Use 'EntityID' type hint if this is an entity reference."
                        )

                    elif self._is_container_of_entity_ref(field_type):
                        origin = get_origin(field_type)
                        if origin is list and isinstance(val, list):
                            new_list = []
                            for x in val:
                                if isinstance(x, int) and not isinstance(x, bool):
                                    remapped = id_map.get(
                                        x, EntityID(-1) if x > 0 else x
                                    )
                                    new_list.append(EntityID(remapped))
                                else:
                                    new_list.append(x)
                            setattr(component, field_name, new_list)

                        elif origin is set and isinstance(val, set):
                            new_set = set()
                            for x in val:
                                if isinstance(x, int) and not isinstance(x, bool):
                                    remapped = id_map.get(
                                        x, EntityID(-1) if x > 0 else x
                                    )
                                    new_set.add(EntityID(remapped))
                                else:
                                    new_set.add(x)
                            setattr(component, field_name, new_set)

                    elif self._is_dict_key_entity_ref(field_type):
                        if isinstance(val, dict):
                            new_dict = {}
                            for k, v in val.items():
                                if isinstance(k, int) and not isinstance(k, bool):
                                    new_k = id_map.get(k, EntityID(-1) if k > 0 else k)
                                    if new_k == -1 and k > 0:
                                        continue  # Prune dangling.
                                    new_dict[EntityID(new_k)] = v
                                else:
                                    new_dict[k] = v
                            setattr(component, field_name, new_dict)

        logger.info(f"Loaded {len(entities_data)} entities from data")

    def _is_entity_ref(self, tp: type) -> bool:
        """
        Check if type is EntityID or EntityID | None.

        Args:
            tp (type): The type to check.

        Returns:
            bool: True if it is an EntityID reference.
        """
        if tp is EntityID:
            return True
        origin = get_origin(tp)
        if origin in (
            typing.Union,
            types.UnionType,
        ):  # Check for Optional[EntityID] or EntityID | None
            args = get_args(tp)
            # Optional[T] is Union[T, NoneType]
            return EntityID in args
        return False

    def _is_container_of_entity_ref(self, tp: type) -> bool:
        """
        Check if type is list[EntityID] or set[EntityID].

        Args:
            tp (type): The type to check.

        Returns:
            bool: True if it is a container of EntityID.
        """
        origin = get_origin(tp)
        if origin in (list, set, list, set):
            args = get_args(tp)
            if args and self._is_entity_ref(args[0]):
                return True
        return False

    def _is_dict_key_entity_ref(self, tp: type) -> bool:
        """
        Check if type is dict[EntityID, Any].

        Args:
            tp (type): The type to check.

        Returns:
            bool: True if the key type is EntityID.
        """
        origin = get_origin(tp)
        if origin in (dict, dict):
            args = get_args(tp)
            if args and self._is_entity_ref(args[0]):
                return True
        return False
