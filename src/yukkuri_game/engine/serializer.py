"""
Serialization Module.
"""
from typing import Any, Dict, Type, Optional, Iterable, Set, get_type_hints, get_origin, get_args
import typing
import msgspec
from loguru import logger
from .ecs import World
from .migration import MigrationRegistry
from .types import EntityID

class WorldSerializer:
    """
    Handles serialization and deserialization of the game world.
    """

    def __init__(self, world: World, component_types: Iterable[Type[Any]]):
        self.world = world
        self.component_map = {c.__name__: c for c in component_types}
        self._persistable_type = self.component_map.get("Persistable")
        self._stable_id_type = self.component_map.get("StableIDComponent")

    def serialize_entity(self, entity: int) -> Optional[Dict[str, Any]]:
        """
        Serializes a single entity.
        Returns a dict containing 'entity_id', 'stable_id', 'components'.
        """
        if not self._persistable_type or not self.world.has_component(entity, self._persistable_type):
            return None

        stable_id = None
        if self._stable_id_type:
             stable_id_comp = self.world.try_get_component(entity, self._stable_id_type)
             stable_id = stable_id_comp.id if stable_id_comp else None

        components_data = {}
        # Use get_all_components to retrieve all components for the entity
        all_components = self.world.get_all_components(entity)

        for component in all_components:
            component_type = type(component)
            # Skip components that shouldn't be serialized
            if component_type.__name__ == "PhysicsBody":
                continue

            # Avoid serializing StableIDComponent twice (it's in stable_id field)
            if self._stable_id_type and component_type == self._stable_id_type:
                continue

            try:
                # Using msgspec for efficient serialization if it's a struct/dataclass
                if hasattr(component, "__dataclass_fields__") or isinstance(component, msgspec.Struct):
                    decoded = msgspec.to_builtins(component)
                    # Add version info if available
                    if hasattr(component_type, "_version_"):
                         decoded["_version_"] = getattr(component_type, "_version_")
                    components_data[component_type.__name__] = decoded
                else:
                    # Fallback or skip
                    pass
            except Exception as e:
                logger.warning(f"Failed to serialize component {component_type.__name__} for entity {entity}: {e}")

        return {
            "entity_id": entity,
            "stable_id": stable_id,
            "components": components_data
        }

    def get_persistable_entities_data(self) -> list[Dict[str, Any]]:
        """
        Returns a list of serialized data for all persistable entities.
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

    def save_to_file(self, filepath: str):
        """Saves all persistable entities to a file using MessagePack."""
        entities_data = self.get_persistable_entities_data()
        with open(filepath, "wb") as f:
            f.write(msgspec.msgpack.encode(entities_data))
        logger.info(f"Saved {len(entities_data)} entities to {filepath}")

    def load_from_file(self, filepath: str):
        """
        Loads entities from a file using MessagePack with two-pass reference resolution.
        """
        try:
            with open(filepath, "rb") as f:
                data = f.read()
                entities_data = msgspec.msgpack.decode(data)
        except FileNotFoundError:
            logger.error(f"Save file {filepath} not found.")
            return

        self.load_from_data(entities_data)

    def load_from_data(self, entities_data: list[Dict[str, Any]]) -> None:
        """
        Loads entities from a list of entity data dicts with two-pass reference resolution.
        """
        if not entities_data:
            return

        # Pass 1: Create Entities and Mapping
        id_map: Dict[int, int] = {} # old_id -> new_id
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
                            comp_data = MigrationRegistry.migrate(comp_name, comp_data, saved_version, target_version)

                        component = msgspec.convert(comp_data, comp_class)
                        self.world.add_component(new_entity, component)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize component {comp_name}: {e}")
                else:
                    logger.warning(f"Unknown component type: {comp_name}")

        # Update World's next stable ID
        if hasattr(self.world, "set_next_stable_id"):
            self.world.set_next_stable_id(max_stable_id + 1)

        # Pass 2: Resolve References
        for new_entity in id_map.values():
            all_components = self.world.get_all_components(new_entity)
            for component in all_components:
                # Introspect type hints
                try:
                    type_hints = typing.get_type_hints(component)
                except Exception:
                    # In some cases (e.g. dynamic types or partial mocks), get_type_hints might fail
                    continue

                for field_name, field_type in type_hints.items():
                    if not hasattr(component, field_name):
                        continue

                    val = getattr(component, field_name)
                    if val is None:
                        continue

                    # Check for EntityID
                    if self._is_entity_ref(field_type):
                        # Scalar EntityID
                        if isinstance(val, int) and not isinstance(val, bool):
                            if val in id_map:
                                setattr(component, field_name, EntityID(id_map[val]))
                            elif val > 0:
                                # Dangling reference
                                setattr(component, field_name, EntityID(-1))

                    # Check for List[EntityID] or Set[EntityID]
                    elif self._is_container_of_entity_ref(field_type):
                        origin = get_origin(field_type)
                        if origin is list and isinstance(val, list):
                            new_list = []
                            for x in val:
                                if isinstance(x, int) and not isinstance(x, bool):
                                    remapped = id_map.get(x, EntityID(-1) if x > 0 else x)
                                    new_list.append(EntityID(remapped))
                                else:
                                    new_list.append(x)
                            setattr(component, field_name, new_list)

                        elif origin is set and isinstance(val, set):
                            new_set = set()
                            for x in val:
                                if isinstance(x, int) and not isinstance(x, bool):
                                    remapped = id_map.get(x, EntityID(-1) if x > 0 else x)
                                    new_set.add(EntityID(remapped))
                                else:
                                    new_set.add(x)
                            setattr(component, field_name, new_set)

                    # Check for Dict[EntityID, Any] (Keys)
                    elif self._is_dict_key_entity_ref(field_type):
                         if isinstance(val, dict):
                            new_dict = {}
                            for k, v in val.items():
                                if isinstance(k, int) and not isinstance(k, bool):
                                    new_k = id_map.get(k, EntityID(-1) if k > 0 else k)
                                    # Prune dangling
                                    if new_k == -1 and k > 0:
                                        continue
                                    new_dict[EntityID(new_k)] = v
                                else:
                                    new_dict[k] = v
                            setattr(component, field_name, new_dict)

    def _is_entity_ref(self, tp: Type) -> bool:
        """Check if type is EntityID or Optional[EntityID]"""
        if tp is EntityID:
            return True
        origin = get_origin(tp)
        if origin is typing.Union: # Check for Optional[EntityID]
            args = get_args(tp)
            # Optional[T] is Union[T, NoneType]
            return EntityID in args
        return False

    def _is_container_of_entity_ref(self, tp: Type) -> bool:
        """Check if type is List[EntityID] or Set[EntityID]"""
        origin = get_origin(tp)
        if origin in (list, set, typing.List, typing.Set):
            args = get_args(tp)
            if args and self._is_entity_ref(args[0]):
                return True
        return False

    def _is_dict_key_entity_ref(self, tp: Type) -> bool:
        """Check if type is Dict[EntityID, Any]"""
        origin = get_origin(tp)
        if origin in (dict, typing.Dict):
            args = get_args(tp)
            if args and self._is_entity_ref(args[0]):
                return True
        return False

        logger.info(f"Loaded {len(entities_data)} entities from data")
